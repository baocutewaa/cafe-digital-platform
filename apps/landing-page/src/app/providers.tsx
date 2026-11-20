import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { ChatWidgetProvider } from "@/features/chat/components/ChatWidgetProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ChatWidgetProvider>{children}</ChatWidgetProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
