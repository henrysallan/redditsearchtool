import { 
  collection, 
  doc, 
  setDoc, 
  getDocs, 
  query, 
  orderBy, 
  limit,
  where 
} from 'firebase/firestore';
import { db } from './firebase';

export interface SearchHistoryItem {
  id: string;
  userId: string;
  query: string;
  maxPosts: number;
  model: string;
  useWebSearch: boolean;
  agentCount?: number;
  coordinatorModel?: string;
  summary: string;
  timestamp: Date;
  estimatedCost?: number;
  searchMode?: string;
}

export const saveSearchToHistory = async (
  userId: string, 
  searchData: Omit<SearchHistoryItem, 'id' | 'userId' | 'timestamp'>
): Promise<void> => {
  try {
    const searchId = `search_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const searchRef = doc(db, 'users', userId, 'searches', searchId);
    
    await setDoc(searchRef, {
      ...searchData,
      userId,
      timestamp: new Date(),
    });
  } catch (error) {
    console.error('Error saving search to history:', error);
    throw error;
  }
};

export const getUserSearchHistory = async (userId: string, limitCount: number = 50): Promise<SearchHistoryItem[]> => {
  try {
    const searchesRef = collection(db, 'users', userId, 'searches');
    const q = query(
      searchesRef, 
      orderBy('timestamp', 'desc'), 
      limit(limitCount)
    );
    
    const querySnapshot = await getDocs(q);
    const searches: SearchHistoryItem[] = [];
    
    querySnapshot.forEach((doc) => {
      const data = doc.data();
      searches.push({
        id: doc.id,
        userId: data.userId,
        query: data.query,
        maxPosts: data.maxPosts,
        model: data.model,
        useWebSearch: data.useWebSearch,
        agentCount: data.agentCount,
        coordinatorModel: data.coordinatorModel,
        summary: data.summary,
        timestamp: data.timestamp?.toDate() || new Date(),
        estimatedCost: data.estimatedCost,
        searchMode: data.searchMode,
      });
    });
    
    return searches;
  } catch (error) {
    console.error('Error fetching search history:', error);
    throw error;
  }
};