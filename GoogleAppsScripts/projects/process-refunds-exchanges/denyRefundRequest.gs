function denyRefundRequest(requestData) {
  // MailApp.sendEmail({to: DEBUG_EMAIL, htmlBody: `❌ Denying refund request: ${JSON.stringify(requestData, null, 2)}`})
  try {
    markOrderAsProcessed(rawOrderNumber)
  } catch(e) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "Refunds - Error marking order as processed",
      htmlBody: `error: ${JSON.stringify(e)}`
    })
  }
}
