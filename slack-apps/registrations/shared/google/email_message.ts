export interface EmailSender {
    emailAddress: string;
    name: string;
}

export interface EmailMessage {
    sendAs: EmailSender;
    to: string;
    replyTo?: string;
    cc?: string;
    bcc?: string;
    subject: string;
    htmlBodyParts: string[];
}
