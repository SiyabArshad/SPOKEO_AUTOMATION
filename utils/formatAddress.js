/**
 * Formats address components into the Spokeo URL format.
 * https://www.spokeo.com/{STATE}/{CITY}/{ADDRESS}
 * Rules:
 * Replace spaces in address with -
 * Remove special characters if needed
 * State -> uppercase
 * City -> capitalize first letter
 */

function formatUrlParams(address, city, state) {
  // Replace spaces with hyphens, remove most special characters
  const formattedAddress = address
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
    
  // Capitalize first letter of city
  const formattedCity = city
    .trim()
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('-'); 

  // State to uppercase
  const formattedState = state.trim().toUpperCase();

  return { formattedState, formattedCity, formattedAddress };
}

module.exports = { formatUrlParams };
