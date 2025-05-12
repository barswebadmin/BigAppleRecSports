export const formatDateOnly = (date: Date): string => {
	
	try {
		return date.toLocaleDateString("en-US", {
			year: "2-digit",
			month: "numeric",
			day: "numeric",
		});
	} catch(e) {
		throw new Error(`formatDateOnly failed: ${e}`)
	}
	
};
  
/** Format a time to h:mm AM/PM string */
export const formatTimeOnly = (date: Date): string => {

	try {
		return date.toLocaleTimeString("en-US", {
			hour: "numeric",
			minute: "2-digit",
			hour12: true,
		});
	} catch(e) {
		throw new Error(`formatTimeOnly failed: ${e}`)
	}
	
};

/** Format a single or comma-separated list of dates */
export const formatOffDates = (
	offDates: {type: string, data: string}
	): string => {

	if (offDates.type === 'object') {
		return formatDateOnly(new Date(offDates.data));
	}

	if (offDates.type === "string") {
		const trimmed = offDates.data.trim();
		if (!trimmed) return "";

		if (trimmed.includes(",")) {
		return trimmed
			.split(",")
			.map((s) => s.trim())
			.join(", ");
		}

		return trimmed;
	}

	throw new Error(`Invalid date input:${offDates}. Must be a valid Date or date string.`);
};