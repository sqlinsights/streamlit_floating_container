"""Refactored Python API for streamlit_floating_container.

Improvements over the original __init__.py:

* Registers the CCv2 component **once** at module import time (best practice
  from the CCv2 guide) instead of re-declaring it inside ``show()`` on every
  render.
* Wires up the refactored JS file (``floating_container.refactored.js``) and
  drops the ``advice_for_reload`` reload handshake entirely — the JS now
  hot-updates in place from ``data``.
* Removes the stray ``st.write(HTML)`` debug call that was leaking the raw
  HTML string into the app on import.
* Light cleanups: typed return from the context manager, clearer validation
  errors, no behavior changes to the public surface.
"""

from __future__ import annotations

import streamlit as st
from contextlib import contextmanager
from pathlib import Path
from enum import Enum
from typing import Literal, get_args

component_dir = Path(__file__).parent


class StartPosition(Enum):
    top = "8%"
    middle = "40%"
    bottom = "84%"


PanelWidthType = Literal["small", "medium", "large"]
StartingPositionType = Literal["top", "middle", "bottom"]


@st.cache_data(show_spinner=False)
def _load_component_code() -> tuple[str, str, str]:
    html = (component_dir / "floating_container.html").read_text()
    css = (component_dir / "styles.css").read_text()
    # Use the refactored JS renderer.
    js = (component_dir / "floating_container.js").read_text()
    return html, css, js


_HTML, _CSS, _JS = _load_component_code()

_FLOATING_COMPONENT = st.components.v2.component(
    name="floating_chat",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=False,
)


class FloatingContainer:
    """A floating, draggable panel overlay for Streamlit apps.

    Renders a circular toggle button anchored to the right edge of the
    viewport. Clicking it opens a glassmorphic panel that hovers over the
    app and hosts arbitrary Streamlit content (messages, forms, FAQs,
    chat inputs, etc.).

    The panel supports dragging (vertical reposition of the toggle
    button), expanding to near-fullscreen, and toggling between a
    default and stretched width. When a ``st.chat_input`` is rendered
    directly inside the panel, it is automatically pinned to the bottom
    to mimic Streamlit's native chat layout.

    Only **one** ``FloatingContainer`` instance may be mounted per page;
    attempting to mount a second instance raises ``RuntimeError`` at
    ``panel()`` enter time.

    Parameters
    ----------
    icon:
        Icon shown on the toggle button. Accepts either a Streamlit
        Material icon syntax (e.g. ``":material/chat:"``) or a single
        character (e.g. ``"?"``, ``"★"``).
    label:
        Text displayed in the panel header when the panel is open.
        Defaults to an empty string (no header label).
    width:
        Legacy parameter; currently has no effect and is kept for
        backward compatibility. Use the Stretch Width button in the
        panel UI to toggle width at runtime.
    start_position:
        Initial vertical position of the toggle button. One of
        ``"top"`` (8%), ``"middle"`` (40%), or ``"bottom"`` (84%).
        Defaults to ``"top"``.
    key:
        Unique identifier for this component instance. Used to scope
        session state and enforce the single-instance invariant.
        Defaults to an empty string.
    glassmorphic:
        When ``True``, applies a frosted-glass blur effect to the
        panel. When ``False``, uses a solid theme-aware background.
        Defaults to ``True``.

    Examples
    --------
    Minimal usage::

        fp = FloatingContainer(icon=":material/chat:", label="Help", key="help")
        with fp.panel():
            st.write("Help content here")

    Chat interface with auto-pinned input::

        fp = FloatingContainer(icon=":material/chat:", key="chat")
        with fp.panel():
            for msg in st.session_state.messages:
                with st.chat_message(msg["who"]):
                    st.write(msg["message"])
            st.chat_input("Type a message...", key="in")

    Raises
    ------
    ValueError
        If ``start_position`` is not one of ``"top"``, ``"middle"``,
        or ``"bottom"``.
    RuntimeError
        Raised from ``panel()`` if another ``FloatingContainer``
        instance is already mounted in the current session.
    """

    def __init__(
        self,
        icon: str,
        label: str = "",
        width: PanelWidthType = "medium",
        start_position: StartingPositionType = "top",
        key: str = "",
        glassmorphic: bool = True,
    ):
        self.label = label
        self.icon = self._validate_icon(icon=icon)
        self.start_position = self._validate_start_position(
            start_position=start_position
        )
        self.key = key
        self.glassmorphic = glassmorphic

    @staticmethod
    def _validate_start_position(start_position: str) -> str:
        """Validate ``start_position`` and map it to a CSS top value.

        Parameters
        ----------
        start_position:
            One of ``"top"``, ``"middle"``, ``"bottom"``.

        Returns
        -------
        str
            The corresponding CSS percentage value (e.g. ``"8%"``).

        Raises
        ------
        ValueError
            If ``start_position`` is not a recognized value.
        """
        valid = list(get_args(StartingPositionType))
        if start_position not in valid:
            raise ValueError(
                f"Invalid start_position value: {start_position!r} "
                f"(expected one of {valid})"
            )
        return StartPosition[start_position].value

    @staticmethod
    def _validate_icon(icon: str) -> str | None:
        """Normalize an icon value into the form expected by the frontend.

        Accepts either a single character or Streamlit's Material icon
        syntax (``":material/<name>:"``) and returns the bare name used
        by the frontend renderer. On invalid input, surfaces an
        ``st.error`` and returns ``None``.

        Parameters
        ----------
        icon:
            The raw icon value supplied by the caller.

        Returns
        -------
        str or None
            The normalized icon value, or ``None`` when the input is
            invalid.
        """
        if len(icon) == 1:
            return icon
        if icon.startswith(":material/") and icon.endswith(":"):
            return icon.removeprefix(":material/").removesuffix(":")
        st.error("Invalid FloatingContainer icon.")
        return None

    @contextmanager
    def panel(self):
        """Mount the floating panel and enter its scrollable container.

        Yields a Streamlit delta generator representing the scrollable
        body of the floating panel. Anything rendered inside the
        ``with`` block appears in the panel. A nested ``with`` is
        **not** required — the yielded value is already the active
        container.

        Enforces the single-instance invariant: if another
        ``FloatingContainer`` instance (with a different key) is
        already mounted in this session, ``RuntimeError`` is raised
        before the component mounts.

        Yields
        ------
        streamlit.delta_generator.DeltaGenerator
            The active scrollable container for the panel body.

        Raises
        ------
        RuntimeError
            If another ``FloatingContainer`` instance is already
            mounted in this session.

        Examples
        --------
        ::

            fp = FloatingContainer(icon=":material/chat:", key="chat")
            with fp.panel():
                st.write("Content in the floating panel")
        """
        instance_key = f"st_floating_container.{self.key}"

        # Enforce the single-instance invariant before we mount.
        active_instances = [
            k
            for k in st.session_state.keys()
            if str(k).startswith("st_floating_container.")
        ]
        if active_instances and instance_key not in active_instances:
            raise RuntimeError(
                "You can only have one instance of FloatingContainer at a time"
            )

        _FLOATING_COMPONENT(
            data=dict(
                icon=self.icon,
                startPosition=self.start_position,
                label=self.label,
                glassmorphic=self.glassmorphic,
            ),
            key=instance_key,
        )
        scrollable = st.container(key="panel-scrollable", border=False)

        with scrollable.container() as e:
            yield e
