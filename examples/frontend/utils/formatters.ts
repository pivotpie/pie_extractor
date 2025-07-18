/**
 * Format bytes to a human-readable string
 * @param bytes - The number of bytes
 * @param decimals - Number of decimal places to show (default: 2)
 * @returns Formatted string with appropriate unit (e.g., "1.23 MB")
 */
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

/**
 * Format a date string to a localized date format
 * @param dateString - ISO date string
 * @param locale - Locale string (default: 'en-US')
 * @returns Formatted date string (e.g., "Jan 1, 2023")
 */
export const formatDate = (
  dateString: string, 
  locale = 'en-US', 
  options: Intl.DateTimeFormatOptions = {}
): string => {
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options
  };
  
  return new Date(dateString).toLocaleDateString(locale, defaultOptions);
};

/**
 * Format a date to a relative time string (e.g., "2 days ago")
 * @param dateString - ISO date string
 * @returns Relative time string
 */
export const formatRelativeTime = (dateString: string): string => {
  const now = new Date();
  const date = new Date(dateString);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
    second: 1
  };
  
  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return interval === 1 
        ? `${interval} ${unit} ago` 
        : `${interval} ${unit}s ago`;
    }
  }
  
  return 'just now';
};

/**
 * Truncate text to a specified length and add an ellipsis if needed
 * @param text - The text to truncate
 * @param maxLength - Maximum length before truncation
 * @param ellipsis - The ellipsis string to append (default: '...')
 * @returns Truncated text with ellipsis if needed
 */
export const truncateText = (text: string, maxLength: number, ellipsis = '...'): string => {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}${ellipsis}`;
};

/**
 * Format a number as a currency string
 * @param amount - The amount to format
 * @param currency - ISO 4217 currency code (default: 'USD')
 * @param locale - Locale string (default: 'en-US')
 * @returns Formatted currency string (e.g., "$1,234.56")
 */
export const formatCurrency = (
  amount: number, 
  currency = 'USD', 
  locale = 'en-US'
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Format a number with a specific number of decimal places
 * @param num - The number to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted number as a string
 */
export const formatNumber = (num: number, decimals = 2): string => {
  return num.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

/**
 * Format a string to title case
 * @param str - The string to format
 * @returns String in title case (e.g., "Hello World")
 */
export const toTitleCase = (str: string): string => {
  return str.replace(
    /\w\S*/g,
    (txt) => txt.charAt(0).toUpperCase() + txt.substring(1).toLowerCase()
  );
};
