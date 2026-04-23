
const INSTANCES = new WeakMap();

const ICONS = {
    close: '<svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="20px" fill="var(--st-text-color)"><path d="M522-480 333-669l51-51 240 240-240 240-51-51 189-189Z"/></svg>',
    expand: '<svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="20px" fill="var(--st-text-color)"><path d="M200-200v-240h80v160h160v80H200Zm480-320v-160H520v-80h240v240h-80Z"/></svg>',
    collapse: '<svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="20px" fill="var(--st-text-color)"><path d="M440-440v240h-80v-160H200v-80h240Zm160-320v160h160v80H520v-240h80Z"/></svg>',
    horizontal: '<svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="24px" fill="var(--st-text-color)"><path d="M160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h640q33 0 56.5 23.5T880-720v480q0 33-23.5 56.5T800-160H160Zm640-560H160v480h640v-480Zm-640 0v480-480Zm200 360v-240L240-480l120 120Zm360-120L600-600v240l120-120Z"/></svg>',
};

const panelIcon = (icon) =>
    `<span class="open-panel-btn-text material-symbols-outlined" data-testid="stIconMaterial" translate="no">${icon}</span>`;

export default function (component) {
    const { data, parentElement } = component;

    // ---- Resolve or create the per-instance state ----
    let instance = INSTANCES.get(parentElement);
    if (!instance) {
        instance = createInstance(parentElement);
        INSTANCES.set(parentElement, instance);
    }

    // ---- Re-hydrate UI from data on every run ----
    applyData(instance, data);

    // ---- Cleanup: tear down everything when Streamlit unmounts ----
    return () => {
        instance.dispose();
        INSTANCES.delete(parentElement);
    };
}

function createInstance(parentElement) {
    // Scoped DOM references (component's own nodes live under parentElement).
    const openButton = parentElement.querySelector('#open-panel');
    const panelWindow = parentElement.querySelector('#floating-panel');
    const wrapper = parentElement.querySelector('#movable-wrapper');
    const handle = parentElement.querySelector('#drag-handle');
    const labelH2 = panelWindow.querySelector('#label');
    const closeBtn = parentElement.querySelector('#close-panel');
    const expandBtn = parentElement.querySelector('#expand-panel');
    const messagesScrollableWrapper = parentElement.querySelector('#panel-scrollable');
    const bottomDiv = parentElement.querySelector('#input-div');
    const horizontalExpand = document.getElementById('horizontal-expand');

    // Static icon wiring (close/expand). The panel icon is data-driven and set
    // in applyData().
    closeBtn.innerHTML = ICONS.close;
    expandBtn.innerHTML = ICONS.expand;
    horizontalExpand.innerHTML = ICONS.horizontal;

    const horizontalState = {
        true: '800px',
        false: '400px'
    }

    // ---- Local UI state ----
    let isExpanded = false;
    let isStretched = false;
    let isDragging = false;
    let startY = 0;
    let initialTop = 0;
    let savedTopPosition = null;
    let elementCount = 0;
    let capturedScrollable = null;
    let capturedFixed = null;
    let capturedChats = null;


    // ---- Positioning helpers ----
    const positionPanelWindow = () => {
        const buttonRect = wrapper.getBoundingClientRect();
        const panelHeight = panelWindow.offsetHeight || 400;
        const viewportHeight = window.innerHeight;
        const padding = 20;

        let topPosition = buttonRect.top;
        if (topPosition + panelHeight > viewportHeight - padding) {
            topPosition = viewportHeight - panelHeight - padding;
        }
        if (topPosition < padding) {
            topPosition = padding;
        }

        panelWindow.style.top = `${topPosition}px`;
        panelWindow.style.bottom = '20px';
        savedTopPosition = topPosition;
    };

    const expandToViewport = () => {
        const viewportHeight = window.innerHeight;
        const padding = 40;
        const expandedHeight = (viewportHeight - padding * 2) * 0.95;
        const topPosition = (viewportHeight - expandedHeight) / 2;

        panelWindow.style.top = `${topPosition}px`;
        panelWindow.style.height = `${expandedHeight}px`;
        panelWindow.style.maxHeight = `${expandedHeight}px`;
    };


    const collapseToNormal = () => {
        panelWindow.style.height = '';
        panelWindow.style.maxHeight = '';
        if (savedTopPosition !== null) {
            panelWindow.style.top = `${savedTopPosition}px`;
        } else {
            positionPanelWindow();
        }
    };

    const applyEmptyState = (count) => {
        if (count === 0) {
            bottomDiv.classList.add('empty');
            messagesScrollableWrapper.classList.add('scrollable-panel-is-empty');
        } else {
            bottomDiv.classList.remove('empty');
            messagesScrollableWrapper.classList.remove('scrollable-panel-is-empty');
        }
    };

    // ---- Event handlers ----

    const onOpenClick = () => {
        openButton.classList.add('nav-open');
        openButton.disabled = true;
        panelWindow.classList.add('panel-open');
        closeBtn.classList.add('panel-open');
        handle.classList.add('hidden');
        positionPanelWindow();
    };

    const onCloseClick = () => {
        openButton.classList.remove('nav-open');
        openButton.disabled = false;
        panelWindow.classList.remove('panel-open');
        closeBtn.classList.remove('panel-open');
        handle.classList.remove('hidden');
    };

    const onExpandClick = () => {
        isExpanded = !isExpanded;
        panelWindow.classList.toggle('expanded');
        expandBtn.innerHTML = isExpanded ? ICONS.collapse : ICONS.expand;
        if (isExpanded) {
            expandToViewport();
        } else {
            collapseToNormal();
        }
    };
    const onStretchClick = () => {
        isStretched = !isStretched;
        panelWindow.style.width = horizontalState[isStretched];
        panelWindow.style.maxWidth = horizontalState[isStretched];
        panelWindow.style.minWidth = horizontalState[isStretched];

    };


    const onHandleMouseDown = (e) => {
        isDragging = true;
        wrapper.classList.add('active');
        startY = e.clientY;
        initialTop = wrapper.offsetTop;
        document.body.style.cursor = 'grabbing';
        e.preventDefault();
    };

    const onMouseMove = (e) => {
        if (!isDragging) return;
        const deltaY = e.clientY - startY;
        const viewportHeight = window.innerHeight;
        const minBoundary = viewportHeight * 0.08;
        const maxBoundary = viewportHeight * 0.90;
        const buttonHeight = wrapper.offsetHeight;

        let newTop = initialTop + deltaY;
        newTop = Math.max(newTop, minBoundary);
        newTop = Math.min(newTop, maxBoundary - buttonHeight);
        wrapper.style.top = `${newTop}px`;
    };

    const onMouseUp = () => {
        if (!isDragging) return;
        isDragging = false;
        wrapper.classList.remove('active');
        document.body.style.cursor = 'default';
        if (panelWindow.classList.contains('panel-open')) {
            positionPanelWindow();
        }
    };

    openButton.addEventListener('click', onOpenClick);
    closeBtn.addEventListener('click', onCloseClick);
    expandBtn.addEventListener('click', onExpandClick);
    handle.addEventListener('mousedown', onHandleMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    horizontalExpand.addEventListener('click', onStretchClick)

    // ---- MutationObserver: track element count in the fixed bottom slot ----
    let debounceTimer = null;
    const countObserver = new MutationObserver(() => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const currentCount = bottomDiv.querySelectorAll('div.stElementContainer').length;
            if (currentCount !== elementCount) {
                elementCount = currentCount;
                applyEmptyState(elementCount);
            }
        }, 10);
    });

    countObserver.observe(bottomDiv, { childList: true, subtree: true });


    const captureExternalContainers = () => {
        const scrollable = document.querySelector('div.st-key-panel-scrollable');
        const fixed = document.querySelector('div.st-key-panel-fixed');
        if (scrollable && scrollable.parentElement !== messagesScrollableWrapper) {
            messagesScrollableWrapper.append(scrollable);

        }

        elementCount = bottomDiv.querySelectorAll('div.stElementContainer').length;
        applyEmptyState(elementCount);
    };

    const syncHasChatClass = () => {
        const chatInputs = messagesScrollableWrapper.querySelectorAll(
            'div[data-testid="stElementContainer"]:has(> div[data-testid="stChatInput"]:first-child)'
        );
        if (chatInputs.length > 1) {
            throw (
                '[FloatingContainer] Only one chat widget allowed per floating container. ' +
                `Found ${chatInputs.length}.`
            );
        }
        messagesScrollableWrapper.classList.toggle('has-chat', chatInputs.length >= 1);
    };

    let chatClassDebounce = null;
    const chatClassObserver = new MutationObserver(() => {
        clearTimeout(chatClassDebounce);
        chatClassDebounce = setTimeout(syncHasChatClass, 10);
    });
    chatClassObserver.observe(messagesScrollableWrapper, {
        childList: true,
        subtree: true,
    });

    captureExternalContainers();
    syncHasChatClass();


    // ---- Dispose ----
    const dispose = () => {
        openButton.removeEventListener('click', onOpenClick);
        closeBtn.removeEventListener('click', onCloseClick);
        expandBtn.removeEventListener('click', onExpandClick);
        handle.removeEventListener('mousedown', onHandleMouseDown);
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        horizontalExpand.removeEventListener('click', onStretchClick);

        clearTimeout(debounceTimer);
        countObserver.disconnect();
        clearTimeout(chatClassDebounce);
        chatClassObserver.disconnect();
        messagesScrollableWrapper.classList.remove('has-chat');
    };

    return {
        openButton,
        panelWindow,
        wrapper,
        labelH2,
        // Track last-applied data so applyData() can do cheap diffs.
        lastData: null,
        dispose,
    };
}


function applyData(instance, data) {
    const next = data || {};
    const prev = instance.lastData || {};

    const { startPosition, icon, label, glassmorphic } = next;

    if (icon !== prev.icon) {
        instance.openButton.innerHTML = panelIcon(icon);
    }
    if (label !== prev.label) {
        instance.labelH2.textContent = label ?? '';
    }
    if (startPosition !== prev.startPosition) {
        instance.wrapper.style.top = startPosition ?? '';
    }
    if (glassmorphic !== prev.glassmorphic) {
        instance.panelWindow.classList.toggle('glassmorphic', Boolean(glassmorphic));
    }

    // Ensure the open button is enabled after initial hydration.
    instance.openButton.disabled = false;
    instance.openButton.classList.remove('disabled');

    instance.lastData = next;
}
