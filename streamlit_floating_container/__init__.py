"""Python API for streamlit_floating_container.

Each ``FloatingContainer`` instance receives its own DOM-safe
``instance_id`` derived from ``key``.  That ID is interpolated into
every element ID in the HTML template and into every Streamlit
container key, so multiple instances (or hot-reload re-mounts) never
collide on duplicate IDs.
"""

from __future__ import annotations

import re
import streamlit as st
from contextlib import contextmanager
from pathlib import Path
from enum import Enum
from typing import Literal, get_args
import time

component_dir = Path(__file__).parent


class StartPosition(Enum):
    top = "8%"
    middle = "40%"
    bottom = "84%"


PanelWidthType = Literal["small", "medium", "large"]
StartingPositionType = Literal["top", "middle", "bottom"]


@st.cache_data(show_spinner=False)
def _load_component_code() -> tuple[str, str, str]:
    """Load the raw HTML/CSS/JS sources (HTML still contains placeholders)."""
    html = (component_dir / "floating_container.html").read_text()
    css = (component_dir / "styles.css").read_text()
    js = (component_dir / "floating_container.js").read_text()
    return html, css, js


_HTML_TEMPLATE, _CSS, _JS = _load_component_code()

# One registered CCv2 component per unique instance_id. Each instance gets
# its own HTML (with IDs rewritten to include the instance_id) so multiple
# instances never share DOM IDs.
_COMPONENT_REGISTRY: dict[str, object] = {}


_INSTANCE_ID_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")


def _slugify_instance_id(raw: str) -> str:
    """Normalize a user-supplied key into a DOM-safe instance ID.

    Replaces runs of non-``[a-zA-Z0-9_-]`` characters with ``-``, trims
    leading/trailing separators, and falls back to ``default`` when the
    result would be empty.
    """
    slug = _INSTANCE_ID_SAFE.sub("-", raw or "").strip("-_")
    return slug or "default"


def _get_component(instance_id: str):
    """Return (and memoize) a CCv2 component whose HTML is parameterized for ``instance_id``."""
    component = _COMPONENT_REGISTRY.get(instance_id)
    if component is not None:
        return component

    html = _HTML_TEMPLATE.replace("__INSTANCE__", instance_id)
    component = st.components.v2.component(
        name=f"floating_chat__{instance_id}",
        html=html,
        css=_CSS,
        js=_JS,
        isolate_styles=False,
    )
    _COMPONENT_REGISTRY[instance_id] = component
    return component


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

    Only one ``FloatingContainer`` instance per ``start_position``
    (``"top"``, ``"middle"``, ``"bottom"``) may be mounted at the same
    time. Attempting to mount a second instance with the same
    ``start_position`` raises ``RuntimeError`` at ``panel()`` enter
    time. When a user opens one panel, all other mounted panels close
    automatically (mutual exclusion is coordinated in the frontend).

    Every DOM ID and Streamlit container key emitted by this component
    is suffixed with a DOM-safe ``instance_id`` derived from ``key``,
    so multiple registrations (across pages or hot reloads) do not
    collide on duplicate IDs.

    Parameters
    ----------
    icon:
        Icon shown on the toggle button. Accepts either a Streamlit
        Material icon syntax (e.g. ``":material/chat:"``) or a single
        character (e.g. ``"?"``, ``"★"``).
    label:
        Text displayed in the panel header when the panel is open.
    width:
        Legacy parameter; currently has no effect and is kept for
        backward compatibility.
    start_position:
        Initial vertical position of the toggle button. One of
        ``"top"``, ``"middle"``, ``"bottom"``.
    key:
        Unique identifier for this component instance. Used to derive
        a DOM-safe ``instance_id`` and to scope the single-instance
        invariant.
    glassmorphic:
        When ``True``, applies a frosted-glass blur effect to the panel.

    Examples
    --------
    ::

        fp = FloatingContainer(icon=":material/chat:", key="chat")
        with fp.panel():
            st.write("Content in the floating panel")

    Raises
    ------
    ValueError
        If ``start_position`` is not one of ``"top"``, ``"middle"``, or
        ``"bottom"``.
    RuntimeError
        Raised from ``panel()`` if another ``FloatingContainer`` with a
        different key is already mounted in this session.
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
        # Keep the literal name ("top"/"middle"/"bottom") for the
        # single-per-position check, and resolve the CSS value for the
        # renderer.
        self.start_position_key = self._validate_start_position_key(
            start_position=start_position
        )
        self.start_position = StartPosition[self.start_position_key].value
        self.key = key
        self.glassmorphic = glassmorphic

        # DOM-safe instance ID used to parameterize all HTML IDs and
        # Streamlit container keys.
        self.instance_id = _slugify_instance_id(key)

    @staticmethod
    def _validate_start_position_key(start_position: str) -> str:
        """Validate ``start_position`` and return the literal key."""
        valid = list(get_args(StartingPositionType))
        if start_position not in valid:
            raise ValueError(
                f"Invalid start_position value: {start_position!r} "
                f"(expected one of {valid})"
            )
        return start_position

    @staticmethod
    def _validate_icon(icon: str) -> str | None:
        """Normalize an icon value into the form expected by the frontend."""
        if len(icon) == 1:
            return icon
        if icon.startswith(":material/") and icon.endswith(":"):
            return icon.removeprefix(":material/").removesuffix(":")
        st.error("Invalid FloatingContainer icon.")
        return None

    # --- Key helpers ------------------------------------------------------
    @property
    def _mount_key(self) -> str:
        return f"st_floating_container.{self.instance_id}"

    @property
    def _scrollable_key(self) -> str:
        return f"panel-scrollable-{self.instance_id}"

    @property
    def _fixed_key(self) -> str:
        return f"panel-fixed-{self.instance_id}"

    # --- Public API -------------------------------------------------------
    @contextmanager
    def panel(self):
        """Mount the floating panel and enter its scrollable container.

        Enforces that no other ``FloatingContainer`` with the same
        ``start_position`` is already mounted in this session.
        """
        # Track which positions are currently occupied. Map of
        # start_position -> mount_key so the same instance can re-mount
        # across reruns without tripping the check.
        registry_key = "_st_floating_container_positions"
        registry: dict[str, str] = st.session_state.setdefault(registry_key, {})

        # Prune stale entries: if a mount_key is no longer in session_state
        # (the instance was unmounted), drop it from the registry.
        for pos, mk in list(registry.items()):
            if mk not in st.session_state:
                registry.pop(pos, None)

        occupying = registry.get(self.start_position_key)
        if occupying is not None and occupying != self._mount_key:
            raise RuntimeError(
                "Only one FloatingContainer per start_position is allowed. "
                f"Position {self.start_position_key!r} is already in use."
            )
        registry[self.start_position_key] = self._mount_key

        component = _get_component(self.instance_id)
        component(
            data=dict(
                icon=self.icon,
                startPosition=self.start_position,
                label=self.label,
                glassmorphic=self.glassmorphic,
                instanceId=self.instance_id,
                scrollableKey=self._scrollable_key,
                fixedKey=self._fixed_key,
            ),
            key=self._mount_key,
        )
        scrollable = st.container(key=self._scrollable_key, border=False)
        with scrollable.container() as e:
            yield e
