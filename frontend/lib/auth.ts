import { config } from './config';
import type { TokenPair } from '@/types';

class TokenService {
  private accessToken: string | null = null;
  private refreshTokenValue: string | null = null;
  private expiresAt: number | null = null;

  async fetchTokens(): Promise<TokenPair> {
    const response = await fetch(config.auth.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to obtain tokens' }));
      throw new Error(error.detail || 'Failed to obtain tokens');
    }

    const tokens: TokenPair = await response.json();
    this.setTokens(tokens);
    return tokens;
  }

  async getAccessToken(): Promise<string | null> {
    if (!this.accessToken || !this.expiresAt) {
      return null;
    }

    const now = Date.now();
    const bufferTime = 5 * 60 * 1000; // 5 minutes before expiry

    // Check if token is expired or will expire soon
    if (now >= this.expiresAt - bufferTime) {
      console.log('Access token expired or expiring soon, refreshing...');
      return await this.refreshToken();
    }

    return this.accessToken;
  }

  async refreshToken(): Promise<string | null> {
    if (!this.refreshTokenValue) {
      this.clearTokens();
      return null;
    }

    try {
      const response = await fetch(config.auth.refreshEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshTokenValue }),
      });

      if (!response.ok) {
        console.error('Token refresh failed');
        this.clearTokens();
        return null;
      }

      const tokens: TokenPair = await response.json();
      this.setTokens(tokens);
      return this.accessToken;
    } catch (error) {
      console.error('Error refreshing token:', error);
      this.clearTokens();
      return null;
    }
  }

  private setTokens(tokens: TokenPair): void {
    this.accessToken = tokens.access_token;
    this.refreshTokenValue = tokens.refresh_token;
    this.expiresAt = Date.now() + (tokens.expires_in * 1000);
  }

  clearTokens(): void {
    this.accessToken = null;
    this.refreshTokenValue = null;
    this.expiresAt = null;
  }

  hasTokens(): boolean {
    return !!this.accessToken;
  }
}

export const tokenService = new TokenService();
