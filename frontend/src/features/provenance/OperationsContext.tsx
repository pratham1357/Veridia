import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getOperations } from "../../services/api";
import type { Operation } from "../../types/evidence";
import type { OperationInfo } from "../../types/provenance";
import { fallbackOperation } from "../operations";

interface OperationsState {
  operations: OperationInfo[];
  info: (op: Operation) => OperationInfo;
  label: (op: Operation) => string;
  outputLabel: (op: Operation) => string;
}

const Ctx = createContext<OperationsState | null>(null);

/** Loads the backend's operation registry once, so new operations get proper labels without a frontend change. */
export function OperationsProvider({ children }: { children: ReactNode }) {
  const [operations, setOperations] = useState<OperationInfo[]>([]);

  useEffect(() => {
    getOperations().then(setOperations).catch(() => setOperations([]));
  }, []);

  const info = useCallback(
    (op: Operation) => operations.find((o) => o.name === op) ?? fallbackOperation(op),
    [operations],
  );
  const label = useCallback((op: Operation) => info(op).label, [info]);
  const outputLabel = useCallback((op: Operation) => info(op).output_label, [info]);

  return <Ctx.Provider value={{ operations, info, label, outputLabel }}>{children}</Ctx.Provider>;
}

export function useOperations(): OperationsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useOperations must be used within OperationsProvider");
  return ctx;
}
