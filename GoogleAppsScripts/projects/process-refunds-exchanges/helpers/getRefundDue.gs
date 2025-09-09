const getRefundDue = (
    seasonStartDateStr,
    offDatesStr,
    originalCost,
    refundOrCredit,
    requestSubmittedAt = new Date()
  ) => {
      if (!seasonStartDateStr || !originalCost || !refundOrCredit) return 'Error calculating refund due - please check order and product'
      if (originalCost === 0) {
          return "*Refund Due*: $0 (No payment was made for this order) \n";
      }

      // Current time in UTC (assumes runtime is UTC-safe)

      const [month, day, year] = seasonStartDateStr.split("/").map(Number);
      const normalizedYear = year < 100 ? 2000 + year : year;
      const seasonStartDate = new Date(
          Date.UTC(normalizedYear, month - 1, day, 7, 0, 0)
      );

      let weekDates = [new Date(seasonStartDate)];
      for (let i = 1; i < 5; i++) {
          const nextWeek = new Date(weekDates[i - 1]);
          nextWeek.setUTCDate(nextWeek.getUTCDate() + 7);
          weekDates.push(nextWeek);
      }

      // Parse off dates
      const offDates = (offDatesStr || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((dateStr) => {
            const [m, d, y] = dateStr.split("/").map(Number);
            const normalizedYear = y < 100 ? 2000 + y : y;
            return new Date(Date.UTC(normalizedYear, m - 1, d, 7, 0, 0));
        });

      // Adjust weekDates by shifting subsequent weeks for each offDate
      for (const offDate of offDates.sort((a, b) => a - b)) {
          for (let i = 0; i < weekDates.length; i++) {
              if (weekDates[i].getTime() === offDate.getTime()) {
                  for (let j = i; j < weekDates.length; j++) {
                      weekDates[j] = new Date(
                          weekDates[j].getTime() + 7 * 24 * 60 * 60 * 1000
                      );
                  }
                  break;
              }
          }
      }

      const earlyTierCutoff = new Date(weekDates[0].getTime() - 14 * 24 * 60 * 60 * 1000);
      weekDates.unshift(earlyTierCutoff); // Now weekDates[0] is the earliest tier

      const refundTiers =
          refundOrCredit === "refund"
              ? [95, 90, 80, 70, 60, 50]
              : [100, 95, 85, 75, 65, 55];

      const penalties = [0, 5, 15, 25, 35, 45];
      const addProcessing = refundOrCredit === "refund";

      let refund = 0;
      let penalty = 0;
      Logger.log(`📅 Season Start Date (UTC @ 7am): ${seasonStartDate.toISOString()}`);
      Logger.log(`🕓 Now (UTC): ${JSON.stringify(requestSubmittedAt)}`);
      for (let i = 0; i < weekDates.length; i++) {
        console.log(`checking against week ${i}: ${JSON.stringify(weekDates[i])}. check? ${requestSubmittedAt < weekDates[i]}`)
          if (requestSubmittedAt < weekDates[i]) {
              refund = refundTiers[i];
              penalty = penalties[i];
              break;
          }
      }

      if (refund === 0) {
        return [0, "*Estimated Refund Due*: $0 (No refund — the request came after week 5 had already started) \n"];
      }

      const refundAmount = (refund / 100) * originalCost;
      const refundWeekIndex = refundTiers.indexOf(refund);

      let timingDescription;
      if (refundWeekIndex === 0) {
        timingDescription = "more than 2 weeks before week 1 started";
      } else if (refundWeekIndex === 1) {
        timingDescription = "before week 1 started";
      } else {
        const actualWeek = refundWeekIndex - 1;
        timingDescription = `after the start of week ${actualWeek}`;
      }

      const refundText = `*Estimated Refund Due*: $${refundAmount.toFixed(2)} \n (This request is calculated to have been submitted ${timingDescription}. ${refund}% after ${penalty}% penalty${addProcessing ? " + 5% processing fee" : ""}) \n`;

      return [refundAmount, refundText]
  }