import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

// Internationalization middleware. Route-level role gating is applied in the
// portal layouts (server components) via the NextAuth session; keeping auth out
// of the edge middleware avoids bundling the Keycloak provider at the edge.
export default createMiddleware(routing);

export const config = {
  matcher: ["/", "/(fr|ar)/:path*", "/((?!api|_next|_vercel|.*\\..*).*)"],
};
