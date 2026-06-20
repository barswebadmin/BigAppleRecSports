/**
 * TypeScript types for your Firebase data models
 * Pure TypeScript - defines your data structure
 */

export interface Registration {
  id: string;
  userId: string;
  leagueName: string;
  timestamp: string;
  status: 'pending' | 'confirmed' | 'cancelled';
  paymentStatus?: 'unpaid' | 'paid' | 'refunded';
}

export interface WaitlistEntry {
  id: string;
  userId: string;
  leagueName: string;
  position: number;
  joinedAt: string;
}

export interface User {
  id: string;
  slackUserId: string;
  email: string;
  name: string;
  preferences: {
    notifications: boolean;
    leagues: string[];
  };
}

export interface League {
  id: string;
  name: string;
  season: string;
  maxCapacity: number;
  currentCount: number;
  registrationOpen: boolean;
  startDate: string;
  endDate: string;
}