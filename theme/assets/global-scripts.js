// === Global Helper Functions ===

/**
 * Displays a non-blocking notification banner at the top of the page.
 * @param {string} message The text to display in the banner.
 * @param {string} [type='info'] The type of banner ('success', 'error', or 'info').
 * @param {number} [duration=3000] The time in milliseconds for the banner to be visible.
 */
window.displayBanner = function(message, type = 'info', duration = 3000) {
  // Find or create the main container for all banners
  let container = document.getElementById('global-banner-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'global-banner-container';
    document.body.appendChild(container);
  }

  // Create the new banner element
  const banner = document.createElement('div');
  banner.className = `global-banner banner-${type}`; // e.g., 'global-banner banner-success'
  banner.textContent = message;

  // Add the banner to the container
  container.appendChild(banner);

  // Trigger the fade-in animation
  // We use a short timeout to allow the browser to render the element first
  setTimeout(() => {
    banner.classList.add('visible');
  }, 10);

  // Set a timer to remove the banner
  setTimeout(() => {
    // Trigger the fade-out animation
    banner.classList.remove('visible');

    // After the animation finishes, remove the element from the DOM
    setTimeout(() => {
      if (banner.parentNode) {
        banner.parentNode.removeChild(banner);
      }
    }, 300); // This should match the CSS transition duration
  }, duration);
};