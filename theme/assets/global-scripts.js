// ============================================================================
// ===                      GLOBAL HELPER FUNCTIONS                         ===
// ============================================================================
// This file contains globally accessible JavaScript utility functions for the
// Anvil application. They can be called from any form's Python code using
// anvil.js.call_js('functionName', ...args).

/**
 * Ensures the global modal root container exists in the DOM.
 * This should be called once when the application starts.
 */
window.initializeModalRoot = function() {
  if (!document.getElementById('global-modal-root')) {
    const modalRoot = document.createElement('div');
    modalRoot.id = 'global-modal-root';
    document.body.appendChild(modalRoot);
    // When clicking the dark overlay, find the currently active modal and close it.
    modalRoot.addEventListener('click', (e) => {
      if (e.target.id === 'global-modal-root') {
        const activeModal = modalRoot.querySelector('.modal.active');
        if (activeModal) {
          window.closeModal(activeModal.id);
        }
      }
    });
  }
};

// Call the initialization function immediately.
document.addEventListener('DOMContentLoaded', window.initializeModalRoot);

/**
 * Creates a new logger instance with a specific context name.
 * This allows for standardized, filterable logging from any form.
 * @param {string} contextName - The name of the form or component (e.g., 'AudioManagerForm').
 * @returns {object} A logger object with log, debug, warn, and error methods.
 */
window.createLogger = function(contextName) {
  // Helper function to format the current time as HH:MM:SS
  const getTimestamp = () => {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  };

  const prefix = `[JS:${contextName}]`;

  return {
    log: function(...args) {
      console.log(`[${getTimestamp()}]`, prefix, ...args);
    },
    debug: function(...args) {
      // Use debug for verbose, development-only messages.
      console.debug(`[${getTimestamp()}]`, prefix, ...args);
    },
    warn: function(...args) {
      console.warn(`[${getTimestamp()}]`, prefix, ...args);
    },
    error: function(...args) {
      console.error(`[${getTimestamp()}]`, prefix, ...args);
    }
  };
};

/**
 * Displays a non-blocking notification banner at the top of the page.
 * @param {string} message The text to display in the banner.
 * @param {string} [type='info'] The type of banner ('success', 'error', or 'info').
 * @param {number} [duration=3000] The time in milliseconds for the banner to be visible.
 */
window.displayBanner = function(message, type = 'info', duration = 3000) {
  let container = document.getElementById('global-banner-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'global-banner-container';
    document.body.appendChild(container);
  }
  const banner = document.createElement('div');
  banner.className = `global-banner banner-${type}`;
  banner.textContent = message;
  container.appendChild(banner);
  setTimeout(() => {
    banner.classList.add('visible');
  }, 10);
  setTimeout(() => {
    banner.classList.remove('visible');
    setTimeout(() => {
      if (banner.parentNode) {
        banner.parentNode.removeChild(banner);
      }
    }, 300);
  }, duration);
};

/**
 * Sets the text content of an element by its ID. Ideal for labels, titles, buttons, etc.
 * @param {string} elementId The ID of the target element.
 * @param {string} newText The new text to display.
 */
window.setElementText = function(elementId, newText) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = newText;
  } else {
    console.warn(`setElementText: Element with ID '${elementId}' not found.`);
  }
};

/**
 * Sets the placeholder attribute of an input element by its ID.
 * @param {string} elementId The ID of the target input element.
 * @param {string} newText The new placeholder text.
 */
window.setPlaceholder = function(elementId, newText) {
  const element = document.getElementById(elementId);
  if (element) {
    element.placeholder = newText;
  } else {
    console.warn(`setPlaceholder: Element with ID '${elementId}' not found.`);
  }
};

/**
 * Sets the value of a form input element (like <input> or <textarea>) by its ID.
 * @param {string} elementId The ID of the target input element.
 * @param {string} newValue The new value to set.
 */
window.setValue = function(elementId, newValue) {
  const element = document.getElementById(elementId);
  if (element) {
    element.value = newValue;
  } else {
    console.warn(`setValue: Element with ID '${elementId}' not found.`);
  }
};

/**
 * Sets the HTML title attribute of an element, which appears as a tooltip on hover.
 * @param {string} elementId The ID of the target element.
 * @param {string} newTitle The new title text for the tooltip.
 */
window.setElementTitle = function(elementId, newTitle) {
  const element = document.getElementById(elementId);
  if (element) {
    element.title = newTitle;
  } else {
    console.warn(`setElementTitle: Element with ID '${elementId}' not found.`);
  }
};

/**
 * Shows or hides an element by toggling its display style.
 * @param {string} elementId The ID of the target element.
 * @param {boolean} isVisible If true, sets display to its default; if false, sets to 'none'.
 */
window.setElementVisibility = function(elementId, isVisible) {
  const element = document.getElementById(elementId);
  if (element) {
    element.style.display = isVisible ? '' : 'none';
  } else {
    console.warn(`setElementVisibility: Element with ID '${elementId}' not found.`);
  }
};

/**
 * Enables or disables a button and adds/removes a 'disabled' class for styling.
 * @param {string} buttonId The ID of the target button element.
 * @param {boolean} isEnabled If true, enables the button; if false, disables it.
 */
window.setButtonEnabled = function(buttonId, isEnabled) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = !isEnabled;
    button.classList.toggle('disabled', !isEnabled);
  } else {
    console.warn(`setButtonEnabled: Button with ID '${buttonId}' not found.`);
  }
};

/**
 * Gets the value of a form input element (like <input> or <textarea>) by its ID.
 * @param {string} elementId The ID of the target input element.
 * @returns {string|null} The value of the element, or null if not found.
 */
window.getValueById = function(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    return element.value;
  }
  // C'est une bonne pratique d'afficher un avertissement si l'élément n'est pas trouvé.
  console.warn(`getValueById: Element with ID '${elementId}' not found.`);
  return null;
};

/**
 * Opens a modal dialog by its ID by adding an 'active' class.
 * @param {string} modalId The ID of the modal element to show.
 */
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  const modalRoot = document.getElementById('global-modal-root');

  if (modal && modalRoot) {
    // Store the original parent to return the modal later
    modal.dataset.originalParentId = modal.parentElement.id || `anvil-component-${Date.now()}`;
    if (!modal.parentElement.id) {
      modal.parentElement.id = modal.dataset.originalParentId;
    }

    modalRoot.appendChild(modal); // Move modal to the portal
    modalRoot.style.display = 'flex'; // Show the portal overlay
    modal.classList.add('active');
  } else {
    console.warn(`openModal: Element with ID '${modalId}' or '#global-modal-root' not found.`);
  }
};

/**
 * Closes a modal dialog by its ID by removing an 'active' class.
 * @param {string} modalId The ID of the modal element to hide.
 */
window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  const modalRoot = document.getElementById('global-modal-root');
  const originalParent = document.getElementById(modal.dataset.originalParentId);

  if (modal && modalRoot) {
    modal.classList.remove('active');
    modalRoot.style.display = 'none'; // Hide the portal overlay

    // Return the modal to its original parent so Anvil doesn't lose track of it
    if (originalParent) {
      originalParent.appendChild(modal);
    }
  } else {
    console.warn(`closeModal: Element with ID '${modalId}' or '#global-modal-root' not found.`);
  }
};