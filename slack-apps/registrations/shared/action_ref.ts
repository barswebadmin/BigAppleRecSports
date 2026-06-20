/** Authorization and routing fields carried by every remotely-dispatched action.
 *  T is the action-specific context (e.g. order ids for a refund, player id for
 *  a roster change). Intersected so all T fields are top-level on the ref. */
export type ActionRef<T extends Record<string, unknown> = Record<string, unknown>> = T & {
    /** Slack user id of the approver — audit trail. */
    approvedBy: string;
    /** Routes the remote handler to its test path (no live mutations). */
    isTest: boolean;
};
