import { doc, getDoc, setDoc, updateDoc, increment } from 'firebase/firestore';
import { db } from './firebase';

// Cookie management utilities
export const getCookie = (name: string): string | null => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
};

export const setCookie = (name: string, value: string, days: number = 30): void => {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
};

// Usage tracking constants
export const ANONYMOUS_SEARCH_LIMIT = 1;
export const FREE_USER_DAILY_LIMIT = Infinity; // Unlimited for signed-in users
export const ANONYMOUS_COOKIE_NAME = 'reddit_search_count';

// User tier definitions
export type UserTier = 'anonymous' | 'free' | 'paid';

export const getUserTier = (user: any): UserTier => {
  if (!user) return 'anonymous';
  // For now, all signed-in users are 'free' tier
  // Later we'll add subscription logic here
  return 'free';
};

// Model access control
export const getAvailableModels = (tier: UserTier) => {
  switch (tier) {
    case 'anonymous':
    case 'free':
      return [
        { value: 'gemini-1.5-flash', label: '🆓 Gemini Flash (Free)', isFree: true }
      ];
    case 'paid':
      return [
        { value: 'gemini-1.5-flash', label: '🆓 Gemini Flash (Free)', isFree: true },
        { value: 'gemini-1.5-pro', label: '💎 Gemini Pro', isFree: false },
        { value: 'claude-3-5-sonnet-20241022', label: '💎 Claude 3.5 Sonnet', isFree: false },
        { value: 'claude-3-5-haiku-20241022', label: '💎 Claude 3 Haiku', isFree: false }
      ];
    default:
      return [];
  }
};

export const isModelAllowed = (model: string, tier: UserTier): boolean => {
  const availableModels = getAvailableModels(tier);
  return availableModels.some(m => m.value === model);
};

// Anonymous user tracking
export const getAnonymousSearchCount = (): number => {
  const count = getCookie(ANONYMOUS_COOKIE_NAME);
  return count ? parseInt(count, 10) : 0;
};

export const incrementAnonymousSearchCount = (): number => {
  const currentCount = getAnonymousSearchCount();
  const newCount = currentCount + 1;
  setCookie(ANONYMOUS_COOKIE_NAME, newCount.toString());
  return newCount;
};

export const canAnonymousUserSearch = (): boolean => {
  return getAnonymousSearchCount() < ANONYMOUS_SEARCH_LIMIT;
};

// Authenticated user tracking
export const getUserUsageDoc = (userId: string) => {
  const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
  return doc(db, 'userUsage', `${userId}_${today}`);
};

export const getDailySearchCount = async (userId: string): Promise<number> => {
  try {
    const usageDoc = await getDoc(getUserUsageDoc(userId));
    return usageDoc.exists() ? (usageDoc.data().searchCount || 0) : 0;
  } catch (error) {
    console.error('Error getting daily search count:', error);
    return 0;
  }
};

export const incrementDailySearchCount = async (userId: string): Promise<number> => {
  try {
    const usageDocRef = getUserUsageDoc(userId);
    const usageDoc = await getDoc(usageDocRef);
    
    if (usageDoc.exists()) {
      await updateDoc(usageDocRef, {
        searchCount: increment(1),
        lastUpdated: new Date()
      });
      return (usageDoc.data().searchCount || 0) + 1;
    } else {
      await setDoc(usageDocRef, {
        userId,
        searchCount: 1,
        date: new Date().toISOString().split('T')[0],
        lastUpdated: new Date(),
        createdAt: new Date()
      });
      return 1;
    }
  } catch (error) {
    console.error('Error incrementing daily search count:', error);
    throw error;
  }
};

export const canAuthenticatedUserSearch = async (userId: string): Promise<boolean> => {
  try {
    const count = await getDailySearchCount(userId);
    return count < FREE_USER_DAILY_LIMIT;
  } catch (error) {
    console.error('Error checking if authenticated user can search:', error);
    return false;
  }
};

// Main usage tracking interface
export interface UsageStatus {
  canSearch: boolean;
  searchCount: number;
  limit: number;
  isAuthenticated: boolean;
  requiresSignIn: boolean;
}

export const checkUsageStatus = async (userId?: string): Promise<UsageStatus> => {
  if (userId) {
    // Authenticated user
    const searchCount = await getDailySearchCount(userId);
    const canSearch = searchCount < FREE_USER_DAILY_LIMIT;
    
    return {
      canSearch,
      searchCount,
      limit: FREE_USER_DAILY_LIMIT,
      isAuthenticated: true,
      requiresSignIn: false
    };
  } else {
    // Anonymous user
    const searchCount = getAnonymousSearchCount();
    const canSearch = searchCount < ANONYMOUS_SEARCH_LIMIT;
    
    return {
      canSearch,
      searchCount,
      limit: ANONYMOUS_SEARCH_LIMIT,
      isAuthenticated: false,
      requiresSignIn: !canSearch
    };
  }
};

export const recordSearch = async (userId?: string): Promise<void> => {
  if (userId) {
    await incrementDailySearchCount(userId);
  } else {
    incrementAnonymousSearchCount();
  }
};

// Reset functions for testing
export const resetAnonymousUsage = (): void => {
  document.cookie = `${ANONYMOUS_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
};

export const getUsageMessage = (status: UsageStatus): string => {
  if (status.isAuthenticated) {
    if (status.limit === Infinity) {
      return 'Unlimited';
    } else if (status.canSearch) {
      return `${status.searchCount}/${status.limit} daily searches used`;
    } else {
      return `Daily limit reached (${status.limit} searches). Try again tomorrow!`;
    }
  } else {
    if (status.canSearch) {
      return `${status.searchCount}/${status.limit} free searches used. Sign in for unlimited Gemini searches!`;
    } else {
      return 'Sign in for unlimited Gemini searches!';
    }
  }
};