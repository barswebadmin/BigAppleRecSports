/**
 * Formatting utility functions
 * Handles all formatting for display, sheet updates, and user interaction
 *
 * @fileoverview Formatting utilities for dates, times, and display values
 * @requires ../helpers/formatValidators.gs
 */

/**
 * Helper function to format values for display with specific formatting rules
 */
function formatValue(value, label, formatType = 'default') {
  // Handle TBD values specially first, before checking for empty
  if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
    return `${label}: TBD`;
  }

  if (value === null || value === undefined || value === '') {
    return `${label}: [Not Found]`;
  }

  switch (formatType) {
    case 'price':
      return `${label}: $${value}`;
    case 'time':
      if (value instanceof Date) {
        return `${label}: ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
      } else if (typeof value === 'string' && value.includes(':')) {
        // Try to parse time string
        try {
          const [hours, minutes] = value.split(':');
          const hour = parseInt(hours);
          const min = parseInt(minutes);
          const period = hour >= 12 ? 'PM' : 'AM';
          const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
          return `${label}: ${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
        } catch {
          return `${label}: ${value}`;
        }
      }
      return `${label}: ${value}`;
    case 'datetime':
      if (value instanceof Date) {
        return `${label}: ${formatDateTimeMdYYhm_(value)}`;
      } else if (typeof value === 'string' && value.trim()) {
        // Try to parse ISO date strings
        if (value.includes('T') && (value.includes('Z') || value.includes('+'))) {
          try {
            const dateObj = new Date(value);
            return `${label}: ${formatDateTimeMdYYhm_(dateObj)}`;
          } catch {
            return `${label}: ${value}`;
          }
        }
        return `${label}: ${value}`;
      }
      return `${label}: [Not Found]`;
    case 'date':
      if (value instanceof Date) {
        return `${label}: ${formatDateMdYY_(value)}`;
      } else if (typeof value === 'string' && value.trim()) {
        // Try to parse ISO date strings
        if (value.includes('T') && (value.includes('Z') || value.includes('+'))) {
          try {
            const dateObj = new Date(value);
            return `${label}: ${formatDateMdYY_(dateObj)}`;
          } catch {
            return `${label}: ${value}`;
          }
        }
        return `${label}: ${value}`;
      }
      return `${label}: [Not Found]`;
    default:
      if (value instanceof Date) {
        return `${label}: ${value.toLocaleDateString('en-US')}`;
      }
      return `${label}: ${value}`;
  }
}

/**
 * Format date for sheet display (MM/DD/YYYY)
 */
function formatDateForSheet_(date) {
  if (!(date instanceof Date)) return date;
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const year = date.getFullYear();
  return `${month}/${day}/${year}`;
}

/**
 * Format datetime for sheet display (MM/DD/YYYY HH:MM AM/PM)
 */
function formatDateTimeForSheet_(date) {
  if (!(date instanceof Date)) return date;
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const year = date.getFullYear();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
  const displayMinutes = minutes.toString().padStart(2, '0');
  return `${month}/${day}/${year} ${displayHours}:${displayMinutes} ${period}`;
}

/**
 * Format time for sheet display (HH:MM AM/PM)
 */
function formatTimeForSheet_(date) {
  if (!(date instanceof Date)) return date;
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
  const displayMinutes = minutes.toString().padStart(2, '0');
  return `${displayHours}:${displayMinutes} ${period}`;
}

/**
 * Format datetime for display (M/d/yy at H:mm AM/PM)
 */
function formatDateTimeForDisplay_(date) {
  if (!(date instanceof Date)) return date;
  
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const year = date.getFullYear().toString().slice(-2);
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
  const displayMinutes = minutes.toString().padStart(2, '0');
  
  return `${month}/${day}/${year} at ${displayHours}:${displayMinutes} ${period}`;
}

/**
 * Format time for display
 */
function formatTimeForDisplay_(value) {
  if (value instanceof Date) {
    return value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  } else if (typeof value === 'string' && value.includes(':')) {
    // Try to parse time string
    try {
      const [hours, minutes] = value.split(':');
      const hour = parseInt(hours);
      const min = parseInt(minutes);
      const period = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      return `${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
    } catch {
      return value;
    }
  }
  return value;
}
