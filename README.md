# Streamlit Floating Container

A Streamlit custom component that creates a floating, draggable panel overlay for your Streamlit applications. Perfect for adding chat interfaces, FAQ sections, or any content that needs to be accessible without leaving the current page.

## Features

- **Floating Panel** — a glassmorphic floating panel that hovers over your Streamlit app
- **Draggable** — vertical drag handle to reposition the panel button anywhere on the screen
- **Expandable** — toggle the panel to nearly full viewport height
- **Start Position** — configure the initial button position (top, middle, or bottom)
- **Up to Three Concurrent Panels** — one panel per `start_position` (`top`, `middle`, `bottom`) may be mounted at once
- **Mutual-Exclusion Open** — opening any panel automatically closes all other mounted panels
- **Auto-pinned Chat Input** — `st.chat_input` placed directly inside the container automatically sticks to the bottom, mimicking Streamlit's native chat layout
- **Customizable** — Material icon support, optional label, and glassmorphic toggle
- **Parameterized DOM** — every HTML `id` and Streamlit container `key` is suffixed with a per-instance slug so multiple instances never collide
- **Theme Integration** — automatically adapts to your Streamlit theme colors
- **Resilient to reruns** — component hot-updates in place from props; DOM state survives Streamlit reruns without reload hacks

## Installation

```bash
pip install streamlit-floating-container
```

Using UV:

```bash
uv add streamlit-floating-container
```

## Usage

```python
import streamlit as st
from streamlit_floating_container import FloatingContainer

st.set_page_config(layout="wide")
st.title("My App")

fp = FloatingContainer(
    icon=":material/chat:",
    label="Help",
    start_position="top",
    key="my_float",
    glassmorphic=True,
)

with fp.panel():
    st.subheader("FAQ", anchor=False)
    st.write("Your content here...")
```

### Chat Example

Place `st.chat_input` **directly** inside the container — the component
auto-pins it to the bottom of the panel (via the `has-chat` class on the
scrollable wrapper) so it behaves like Streamlit's native chat layout.

```python
import streamlit as st
from streamlit_floating_container import FloatingContainer

st.set_page_config(layout="wide")
st.title("My App")

if "chats" not in st.session_state:
    st.session_state["chats"] = []

def submit_chat(stkey):
    st.session_state["chats"].append(
        dict(who="user", message=st.session_state[stkey])
    )
    st.session_state["chats"].append(
        dict(who="ai", message="Response message")
    )

fp = FloatingContainer(
    icon=":material/chat:",
    label="Chat",
    start_position="middle",
    key="chat_float",
)

with fp.panel():
    # Message history
    for chat in st.session_state["chats"]:
        with st.chat_message(chat.get("who")):
            st.write(chat.get("message"))

    # Chat input placed directly in the container —
    # auto-pinned to the bottom of the panel.
    st.chat_input(
        "Type a message...",
        key="chat_input",
        on_submit=submit_chat,
        args=["chat_input"],
    )
```

> **Note:** Only **one** `st.chat_input` widget is allowed per floating
> container. Additional chat inputs trigger a console warning and the
> panel will visually anchor the first one it finds.

### FAQ / Static Content Example

```python
import streamlit as st
from streamlit_floating_container import FloatingContainer

fp = FloatingContainer(
    icon=":material/help:",
    label="FAQ",
    start_position="bottom",
    key="faq",
    glassmorphic=False,  # solid background instead of frosted glass
)

with fp.panel():
    st.subheader("Frequently Asked Questions", anchor=False)
    st.markdown("**Q: How do I reset my password?**")
    st.markdown("A: Visit your profile page and click *Reset*.")
    st.divider()
    st.markdown("**Q: Who do I contact for support?**")
    st.markdown("A: Email support@example.com.")
```

### Multiple Panels Example

Up to three panels can coexist — one per start position. Opening any of
them automatically closes the others.

```python
import streamlit as st
from streamlit_floating_container import FloatingContainer

chat = FloatingContainer(
    icon=":material/chat:", label="Chat",
    start_position="top", key="chat",
)
faq = FloatingContainer(
    icon=":material/help:", label="FAQ",
    start_position="middle", key="faq",
)
settings = FloatingContainer(
    icon=":material/settings:", label="Settings",
    start_position="bottom", key="settings",
)

with chat.panel():
    st.write("Chat content...")

with faq.panel():
    st.write("FAQ content...")

with settings.panel():
    st.write("Settings content...")
```

## API Reference

### `FloatingContainer`

```python
FloatingContainer(
    icon: str,
    label: str = "",
    start_position: Literal["top", "middle", "bottom"] = "top",
    key: str = "",
    glassmorphic: bool = True,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `icon` | `str` | required | Material icon (e.g., `:material/chat:`) or single character |
| `label` | `str` | `""` | Label displayed in the panel header |
| `start_position` | `str` | `"top"` | Initial button position: `"top"` (8%), `"middle"` (40%), or `"bottom"` (84%) |
| `key` | `str` | `""` | Unique key for the component instance |
| `glassmorphic` | `bool` | `True` | Enable the frosted-glass / blur panel style |

Only **one** `FloatingContainer` per `start_position` (`"top"`, `"middle"`,
`"bottom"`) may be mounted at a time — giving you up to three concurrent
panels. Attempting to mount a second instance with the same
`start_position` raises `RuntimeError`. Whenever a user opens one panel,
any other mounted panels close automatically (mutual-exclusion is
coordinated via a `window`-level `CustomEvent`).

#### `panel()` context manager

```python
with fp.panel():
    st.write("This appears in the floating panel")
```

`panel()` enters the panel's scrollable container directly — anything
you render inside the `with` block appears in the floating panel. You
do **not** need a second nested `with` statement.

If you render a `st.chat_input(...)` inside the panel, the component
automatically pins it to the bottom. No manual placement required.

## Panel Controls

| Control | Description |
|---------|-------------|
| **Open Button** | Click the floating button to open the panel |
| **Close Button** | X button in the top-right corner |
| **Expand / Collapse** | Toggle between normal size and near-fullscreen |
| **Stretch Width** | Toggle the panel width between the default (`400px`) and stretched (`800px`) |
| **Drag Handle** | Appears on hover on the floating button — drag vertically to reposition |

## Styling

The component uses CSS variables from your Streamlit theme:

- `--st-primary-color` — button and accent colors
- `--st-secondary-background-color` — drag handle background, pinned chat-input background
- `--st-text-color` — text and icon colors

The panel features a glassmorphic design with blur effects and subtle
shadows when `glassmorphic=True`. Set `glassmorphic=False` for a solid
background that matches the theme.

### Classes applied at runtime

All IDs in the markup are suffixed with the instance slug
(e.g. `#floating-panel-chat`); the table below shows the base names.

| Class | Target | Added when |
|-------|--------|------------|
| `panel-open` | `#floating-panel-<id>`, `#close-panel-<id>` | Panel is open |
| `expanded` | `#floating-panel-<id>` | Panel is in expanded (near-fullscreen) mode |
| `glassmorphic` | `#floating-panel-<id>` | `glassmorphic=True` |
| `has-chat` | `#panel-scrollable-<id>` | A chat input is present in the container |
| `scrollable-panel-is-empty` | `#panel-scrollable-<id>` | No elements present |
| `empty` | `#input-div-<id>` | No elements in the fixed bottom slot |
| `nav-open` | `#open-panel-<id>` | Panel is open (used to hide the toggle button) |
| `hidden` | `#drag-handle-<id>` | Panel is open (hide drag handle) |
| `active` | `#movable-wrapper-<id>` | User is dragging the button |

## Implementation Notes

- **CCv2 component.** Built on `st.components.v2.component` — one
  component is registered per unique `instance_id` (derived from
  `key`). HTML IDs are rewritten to include that slug so concurrent
  instances do not share DOM IDs.
- **Parameterized keys.** Streamlit container keys
  (`panel-scrollable-<instance_id>`, `panel-fixed-<instance_id>`) and
  session-state mount keys all carry the instance slug.
- **Per-position invariant.** Only one instance per
  `start_position` may be mounted concurrently; enforced from Python
  at `panel()` enter time.
- **Mutual-exclusion open.** Opening any panel dispatches a
  `window`-level `CustomEvent` (`floating-container:opened`); every
  other mounted instance listens for it and closes itself.
- **No reload handshake.** The component hot-updates from `data` on
  every render; no full-page reload or `localStorage` prop diff.
- **DOM safety.** Streamlit-managed nodes are never moved between
  trees; the component only toggles classes on them, avoiding React
  reconciler crashes (`NotFoundError: insertBefore` / `removeChild`)
  on reruns.
- **Observers.** A `MutationObserver` watches the scrollable area to
  keep the `has-chat` class in sync with the actual presence of a
  chat input, across reruns and conditional renders.

## File Structure

```
streamlit-floating-container/
├── pyproject.toml
├── README.md
└── streamlit_floating_container/
    ├── __init__.py
    ├── floating_container.html
    ├── floating_container.js
    └── styles.css
```

