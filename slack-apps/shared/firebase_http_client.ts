/**
 * Firebase HTTP client for Deno - connects to Python Firebase API
 * Provides the same interface as the direct Firebase client
 * Pure TypeScript - makes HTTP calls to Python Firebase API
 */

import type { Registration, WaitlistEntry, User, League } from "./types.ts";

export class FirebaseHttpClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  /**
   * Add document to Firestore collection
   */
  async addDoc<T = any>(collection: string, data: T): Promise<string> {
    const response = await fetch(`${this.baseUrl}/firestore/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ collection, document: data })
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    return result.id;
  }

  /**
   * Get document from Firestore
   */
  async getDoc<T = any>(collection: string, docId: string): Promise<T | null> {
    const response = await fetch(`${this.baseUrl}/firestore/get/${collection}/${docId}`);

    if (response.status === 404) {
      return null;
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    return { id: docId, ...result.data } as T;
  }

  /**
   * Query collection in Firestore
   */
  async queryCollection<T = any>(collection: string, limit: number = 10): Promise<T[]> {
    const response = await fetch(`${this.baseUrl}/firestore/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ collection, limit })
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    return result.results.map((item: any) => ({ id: item.id, ...item.data })) as T[];
  }

  /**
   * Delete document from Firestore
   */
  async deleteDoc(collection: string, docId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/firestore/delete/${collection}/${docId}`, {
      method: 'DELETE'
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }
  }

  /**
   * Check if Firebase API is healthy
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      const result = await response.json();
      return result.status === 'Firebase API running';
    } catch (error) {
      return false;
    }
  }
}

// Export singleton instance
export const firebaseHttpClient = new FirebaseHttpClient();