/**
 * Deno Firebase Admin SDK - Direct Implementation
 * Provides same API as firebase-admin but uses direct REST calls
 */

export interface ServiceAccountCredentials {
  project_id: string;
  client_email: string;
  private_key: string;
  private_key_id: string;
}

export interface FirebaseConfig {
  credential: ServiceAccountCredentials;
  projectId: string;
  databaseId?: string;
}

export interface DocumentSnapshot {
  id: string;
  exists: boolean;
  data(): any;
  createTime: string;
  updateTime: string;
}

export interface DocumentReference {
  id: string;
  path: string;
  get(): Promise<DocumentSnapshot>;
  set(data: any): Promise<void>;
  update(data: any): Promise<void>;
  delete(): Promise<void>;
}

export interface CollectionReference {
  id: string;
  path: string;
  add(data: any): Promise<DocumentReference>;
  doc(id?: string): DocumentReference;
}

export interface QuerySnapshot {
  size: number;
  empty: boolean;
  docs: DocumentSnapshot[];
}

class DenoDocumentReference implements DocumentReference {
  constructor(
    public id: string,
    public path: string,
    private firestore: DenoFirestore
  ) {}

  async get(): Promise<DocumentSnapshot> {
    return await this.firestore.getDocument(this.path);
  }

  async set(data: any): Promise<void> {
    await this.firestore.setDocument(this.path, data);
  }

  async update(data: any): Promise<void> {
    await this.firestore.updateDocument(this.path, data);
  }

  async delete(): Promise<void> {
    await this.firestore.deleteDocument(this.path);
  }
}

class DenoCollectionReference implements CollectionReference {
  constructor(
    public id: string,
    public path: string,
    private firestore: DenoFirestore
  ) {}

  async add(data: any): Promise<DocumentReference> {
    const docId = crypto.randomUUID();
    const docPath = `${this.path}/${docId}`;
    await this.firestore.setDocument(docPath, data);
    return new DenoDocumentReference(docId, docPath, this.firestore);
  }

  doc(id?: string): DocumentReference {
    const docId = id || crypto.randomUUID();
    const docPath = `${this.path}/${docId}`;
    return new DenoDocumentReference(docId, docPath, this.firestore);
  }
}

export class DenoFirestore {
  private credentials: ServiceAccountCredentials;
  private projectId: string;
  private databaseId: string;
  private accessToken: string | null = null;
  private tokenExpiry: number = 0;

  constructor(config: FirebaseConfig) {
    this.credentials = config.credential;
    this.projectId = config.projectId;
    this.databaseId = config.databaseId || '(default)';
  }

  private async getAccessToken(): Promise<string> {
    if (this.accessToken && Date.now() < this.tokenExpiry) {
      return this.accessToken;
    }

    // Generate JWT
    const header = { alg: 'RS256', typ: 'JWT' };
    const now = Math.floor(Date.now() / 1000);
    const payload = {
      iss: this.credentials.client_email,
      sub: this.credentials.client_email,
      aud: 'https://oauth2.googleapis.com/token',
      iat: now,
      exp: now + 3600,
      scope: 'https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/cloud-platform'
    };

    const privateKeyPem = this.credentials.private_key.replace(/\\n/g, '\n').trim();
    const privateKey = await crypto.subtle.importKey(
      'pkcs8',
      this.pemToArrayBuffer(privateKeyPem),
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false,
      ['sign']
    );

    const headerB64 = this.base64UrlEncode(JSON.stringify(header));
    const payloadB64 = this.base64UrlEncode(JSON.stringify(payload));
    const signatureInput = `${headerB64}.${payloadB64}`;

    const signature = await crypto.subtle.sign(
      'RSASSA-PKCS1-v1_5',
      privateKey,
      new TextEncoder().encode(signatureInput)
    );

    const signatureB64 = this.base64UrlEncode(String.fromCharCode(...new Uint8Array(signature)));
    const jwt = `${signatureInput}.${signatureB64}`;

    // Exchange JWT for access token
    const response = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        assertion: jwt
      })
    });

    if (!response.ok) {
      throw new Error(`Token request failed: ${response.status} ${await response.text()}`);
    }

    const data = await response.json();
    this.accessToken = data.access_token;
    this.tokenExpiry = Date.now() + ((data.expires_in - 60) * 1000);

    return this.accessToken;
  }

  private base64UrlEncode(str: string): string {
    return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  private pemToArrayBuffer(pem: string): ArrayBuffer {
    const b64 = pem
      .replace(/-----BEGIN PRIVATE KEY-----/g, '')
      .replace(/-----END PRIVATE KEY-----/g, '')
      .replace(/\s/g, '');
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  collection(collectionPath: string): CollectionReference {
    return new DenoCollectionReference(
      collectionPath.split('/').pop()!,
      `projects/${this.projectId}/databases/${this.databaseId}/documents/${collectionPath}`,
      this
    );
  }

  async setDocument(path: string, data: any): Promise<void> {
    const token = await this.getAccessToken();
    const url = `https://firestore.googleapis.com/v1/${path}`;

    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(this.convertToFirestoreDocument(data))
    });

    if (!response.ok) {
      throw new Error(`Set document failed: ${response.status} ${await response.text()}`);
    }
  }

  async getDocument(path: string): Promise<DocumentSnapshot> {
    const token = await this.getAccessToken();
    const url = `https://firestore.googleapis.com/v1/${path}`;

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.status === 404) {
      return {
        id: path.split('/').pop()!,
        exists: false,
        data: () => null,
        createTime: '',
        updateTime: ''
      };
    }

    if (!response.ok) {
      throw new Error(`Get document failed: ${response.status} ${await response.text()}`);
    }

    const result = await response.json();
    return {
      id: result.name.split('/').pop()!,
      exists: true,
      data: () => this.convertFromFirestoreDocument(result.fields || {}),
      createTime: result.createTime,
      updateTime: result.updateTime
    };
  }

  async updateDocument(path: string, data: any): Promise<void> {
    return this.setDocument(path, data);
  }

  async deleteDocument(path: string): Promise<void> {
    const token = await this.getAccessToken();
    const url = `https://firestore.googleapis.com/v1/${path}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok && response.status !== 404) {
      throw new Error(`Delete document failed: ${response.status} ${await response.text()}`);
    }
  }

  private convertToFirestoreDocument(obj: any): any {
    const fields: any = {};
    for (const [key, value] of Object.entries(obj)) {
      fields[key] = this.convertValue(value);
    }
    return { fields };
  }

  private convertValue(value: any): any {
    if (typeof value === 'string') {
      return { stringValue: value };
    } else if (typeof value === 'number') {
      return Number.isInteger(value) ?
        { integerValue: value.toString() } :
        { doubleValue: value };
    } else if (typeof value === 'boolean') {
      return { booleanValue: value };
    } else if (value instanceof Date) {
      return { timestampValue: value.toISOString() };
    } else if (Array.isArray(value)) {
      return { arrayValue: { values: value.map(v => this.convertValue(v)) } };
    } else if (value && typeof value === 'object') {
      const fields: any = {};
      for (const [k, v] of Object.entries(value)) {
        fields[k] = this.convertValue(v);
      }
      return { mapValue: { fields } };
    }
    return { nullValue: null };
  }

  private convertFromFirestoreDocument(fields: any): any {
    const result: any = {};
    for (const [key, value] of Object.entries(fields)) {
      result[key] = this.parseValue(value);
    }
    return result;
  }

  private parseValue(value: any): any {
    if (value.stringValue !== undefined) return value.stringValue;
    if (value.integerValue !== undefined) return parseInt(value.integerValue);
    if (value.doubleValue !== undefined) return value.doubleValue;
    if (value.booleanValue !== undefined) return value.booleanValue;
    if (value.timestampValue !== undefined) return new Date(value.timestampValue);
    if (value.arrayValue !== undefined) {
      return value.arrayValue.values?.map((v: any) => this.parseValue(v)) || [];
    }
    if (value.mapValue !== undefined) {
      return this.convertFromFirestoreDocument(value.mapValue.fields || {});
    }
    return null;
  }
}

export function initializeApp(config: FirebaseConfig): { firestore: () => DenoFirestore } {
  const firestore = new DenoFirestore(config);
  return {
    firestore: () => firestore
  };
}