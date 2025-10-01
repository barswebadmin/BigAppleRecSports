function getMatchingRow({ year, season, sport, dayOfPlay }) {
  try {
    const sheetId = "1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc";
    const sheetName = `${season} ${year}`;

    const spreadsheet = SpreadsheetApp.openById(sheetId);
    const sheet = spreadsheet.getSheetByName(sheetName);

    if (!sheet) {
      MailApp.sendEmail({
        to: "web@bigapplerecsports.com",
        subject: "❌ Slack Webhook Error 1",
        htmlBody: `❌ Sheet "${sheetName}" not found.`
    });
      return null;
    }

    const data = sheet.getDataRange().getValues();
    const headers = data[0];


    const columnNames = ["Sport", "Day", "Season", "Year", "Season Start Date", "Season End Date", "Price"];
    const columnIndexes = columnNames.reduce((acc, name) => {
      const colIndex = headers.indexOf(name);
      if (colIndex !== -1) acc[name] = colIndex;
      return acc;
    }, {});


    if (Object.keys(columnIndexes).length !== columnNames.length) {
      MailApp.sendEmail({
        to: "web@bigapplerecsports.com",
        subject: "❌ Slack Webhook Error 2",
        htmlBody: "❌ Missing required columns in the sheet."
    });
      return null;
    }


    for (let i = 1; i < data.length; i++) {
      const row = data[i];


      if (
        row[columnIndexes["Year"]] == year &&
        row[columnIndexes["Season"]].toLowerCase() == season.toLowerCase() &&
        row[columnIndexes["Sport"]].toLowerCase() == sport.toLowerCase() &&
        row[columnIndexes["Day"]].toLowerCase() == dayOfPlay.split(" ")[0].trim().toLowerCase()
      ) {
        MailApp.sendEmail({
          to: "web@bigapplerecsports.com",
          subject: "✅ Success 1",
          htmlBody: `✅ Matching Row Found at Row ${i + 1}: sport: ${sport}, season: ${season}, day: ${dayOfPlay}`
      });
        return {
          rowIndex: i + 1,
          sport: row[columnIndexes["Sport"]],
          dayOfPlay: row[columnIndexes["Day"]],
          season: row[columnIndexes["Season"]],
          year: row[columnIndexes["Year"]],
          seasonStartDate: new Date(row[columnIndexes["Season Start Date"]]),
          seasonEndDate: new Date(row[columnIndexes["Season End Date"]]),
          price: row[columnIndexes["Price"]]
        };
      }
    }
    MailApp.sendEmail({
        to: "web@bigapplerecsports.com",
        subject: "❌ Slack Webhook Error 3",
        htmlBody: `❌ No matching product found in "${sheetName}" tab of Product Sheet! (https://docs.google.com/spreadsheets/d/1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc/edit?gid=0#gid=0) \n\n📌 Please check for typos and try again.`
    });
    return null;

  } catch (error) {
    return {success: false, message: `failed to get matching product! message: ${message}`};
  }
}
