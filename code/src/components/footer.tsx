import { Link } from "@tanstack/react-router";

export function Footer() {
  return (
    <footer className="w-full py-8 px-4 mt-auto border-t border-border/40 bg-background/50 backdrop-blur-sm pb-24 lg:pb-8">
      <div className="max-w-3xl mx-auto text-center space-y-3">
        <h3 className="text-sm font-medium text-foreground">Need help or found an issue?</h3>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-xl mx-auto">
          If you experience any problems, have suggestions, or want to report a bug, feel free to
          contact me.
        </p>
        <div className="pt-2">
          <a
            href="mailto:rishibindal9425@gmail.com"
            className="inline-flex items-center justify-center gap-2 text-sm font-medium text-muted-foreground hover:text-primary hover:underline transition-colors duration-200"
          >
            <span className="text-lg">📧</span> rishibindal9425@gmail.com
          </a>
        </div>
      </div>
    </footer>
  );
}
