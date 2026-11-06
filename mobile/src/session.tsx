import * as SecureStore from "expo-secure-store";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { CYCLE_AWARE_STAGES, type CyclePhase, type Habit, type User } from "./api";

const USER_KEY = "herlife.user";
/** The API has no list-habits endpoint yet, so the phone keeps the last suggestions it was given. */
const HABITS_KEY = "herlife.habits";

interface Session {
  /** `undefined` while the keychain is still being read; `null` means she has not onboarded. */
  user: User | null | undefined;
  signIn: (user: User) => Promise<void>;
  signOut: () => Promise<void>;
  /** Today's phase for cycle-aware life stages, so every screen shares one accent color. */
  phase: CyclePhase | undefined;
  setPhase: (phase: CyclePhase | undefined) => void;
  habits: Habit[];
  setHabits: (habits: Habit[]) => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }): ReactNode {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [phase, setPhase] = useState<CyclePhase | undefined>(undefined);
  const [habits, setHabitsState] = useState<Habit[]>([]);

  useEffect(() => {
    Promise.all([SecureStore.getItemAsync(USER_KEY), SecureStore.getItemAsync(HABITS_KEY)])
      .then(([storedUser, storedHabits]) => {
        setHabitsState(storedHabits ? (JSON.parse(storedHabits) as Habit[]) : []);
        setUser(storedUser ? (JSON.parse(storedUser) as User) : null);
      })
      .catch(() => setUser(null));
  }, []);

  const setHabits = async (next: Habit[]): Promise<void> => {
    await SecureStore.setItemAsync(HABITS_KEY, JSON.stringify(next));
    setHabitsState(next);
  };

  const signIn = async (next: User): Promise<void> => {
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(next));
    setUser(next);
  };
  const signOut = async (): Promise<void> => {
    await Promise.all([SecureStore.deleteItemAsync(USER_KEY), SecureStore.deleteItemAsync(HABITS_KEY)]);
    setUser(null);
    setHabitsState([]);
    setPhase(undefined);
  };

  return <SessionContext.Provider value={{ user, signIn, signOut, phase, setPhase, habits, setHabits }}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}

/** For screens under the tab layout, which only renders once a user exists. */
export function useUser(): User {
  const { user } = useSession();
  if (!user) throw new Error("useUser called before onboarding finished");
  return user;
}

export const isCycleAware = (user: User): boolean => CYCLE_AWARE_STAGES.has(user.life_stage);
