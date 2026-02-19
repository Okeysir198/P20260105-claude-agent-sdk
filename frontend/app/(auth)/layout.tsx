export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full overflow-y-auto bg-muted/40">
      <div className="min-h-full flex items-center justify-center py-4 sm:py-8">
        {children}
      </div>
    </div>
  );
}
