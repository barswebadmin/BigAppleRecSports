/**
 * Firebase client for Firestore operations - DENO COMPATIBLE
 * Uses direct REST API implementation for perfect Deno compatibility
 * Automatically loads credentials from .env file
 */

import { initializeApp, type DenoFirestore, type DocumentReference, type CollectionReference } from './deno_firebase_admin.ts';

// Deno global type declaration
declare global {
  const Deno: {
    env: {
      get(key: string): string | undefined;
      set(key: string, value: string): void;
    };
  };
}

interface ServiceAccountCredentials {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
  auth_provider_x509_cert_url: string;
  client_x509_cert_url: string;
}

export class FirebaseClient {
  private _firestore: DenoFirestore | null = null;

  private async ensureInitialized(): Promise<DenoFirestore> {
    if (this._firestore) {
      return this._firestore;
    }

    // Get credentials from Deno environment (loaded from .env file automatically)
    const credsJson = Deno.env.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS");

    if (!credsJson) {
      throw new Error(
        'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS not found.\n' +
        'Run: deno run --env your-app.ts\n' +
        'Or add credentials to slack-apps/.env file'
      );
    }

    const credentials: ServiceAccountCredentials = JSON.parse(credsJson);

    // Initialize Deno Firebase implementation (bypasses Node.js compatibility issues)
    const app = initializeApp({
      credential: credentials,
      projectId: credentials.project_id,
      databaseId: 'bars-backend-fire-db'
    });

    this._firestore = app.firestore();
    console.log(`✅ Deno Firebase client initialized for: ${credentials.project_id}`);
    return this._firestore;
  }

  /**
   * Get Firestore instance for advanced operations
   */
  async firestore(): Promise<DenoFirestore> {
    return await this.ensureInitialized();
  }

  // Document Operations

  /**
   * Get document from Firestore
   */
  async getDoc<T = Record<string, unknown>>(collection: string, docId: string): Promise<T | null> {
    const firestore = await this.ensureInitialized();
    const doc = await firestore.collection(collection).doc(docId).get();
    return doc.exists ? { id: doc.id, ...doc.data() } as T : null;
  }

  /**
   * Set document in Firestore
   */
  async setDoc<T = Record<string, unknown>>(collection: string, docId: string, data: T): Promise<void> {
    const firestore = await this.ensureInitialized();
    await firestore.collection(collection).doc(docId).set(data);
  }

  /**
   * Add document to Firestore collection
   */
  async addDoc<T = Record<string, unknown>>(collection: string, data: T): Promise<string> {
    const firestore = await this.ensureInitialized();
    const docRef = await firestore.collection(collection).add(data);
    return docRef.id;
  }

  /**
   * Update document in Firestore
   */
  async updateDoc<T = Record<string, unknown>>(collection: string, docId: string, updates: Partial<T>): Promise<void> {
    const firestore = await this.ensureInitialized();
    await firestore.collection(collection).doc(docId).update(updates);
  }

  /**
   * Delete document from Firestore
   */
  async deleteDoc(collection: string, docId: string): Promise<void> {
    const firestore = await this.ensureInitialized();
    await firestore.collection(collection).doc(docId).delete();
  }

  // Collection Operations

  /**
   * Collection helper with type safety
   */
  async collection(path: string): Promise<CollectionReference> {
    const firestore = await this.ensureInitialized();
    return firestore.collection(path);
  }

  /**
   * Document helper with type safety
   */
  async doc(path: string): Promise<DocumentReference> {
    const firestore = await this.ensureInitialized();
    const parts = path.split('/');
    return firestore.collection(parts[0]).doc(parts[1]);
  }
}

// Singleton instance
export const firebaseClient = new FirebaseClient();