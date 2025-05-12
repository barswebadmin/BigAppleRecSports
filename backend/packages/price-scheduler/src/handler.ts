type SchedulePayload = {
	sport: string;
	day: string;
	division: string;
	productGid: string;
	openVariantGid: string;
	waitlistVariantGid: string;
	price: number;
	seasonStartDate: string;
	sportStartTime: string;
	offDatesCommaSeparated: string;
  };
  
  export async function handleSchedulePriceChange(payload: SchedulePayload) {
	console.log("📥 Received payload:", payload);
  
	// 🔁 Simulate AWS call (replace this with real fetch later)
	// const response = await fetch("https://your-aws-endpoint", {
	//   method: "POST",
	//   headers: { "Content-Type": "application/json" },
	//   body: JSON.stringify(payload),
	// });
  
	// const data = await response.json();
	return {
	  status: "success",
	  note: "Mocked AWS call for testing",
	  payload,
	};
  }