import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

/**
 * NextAuth v5 configuration using Keycloak (OIDC).
 * Realm roles are copied from the access token into the session so the UI can
 * gate portals by role. The raw access token is kept for calling the API.
 */
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Keycloak({
      clientId: process.env.AUTH_KEYCLOAK_ID,
      clientSecret: process.env.AUTH_KEYCLOAK_SECRET,
      issuer: process.env.AUTH_KEYCLOAK_ISSUER,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        try {
          const payload = JSON.parse(
            Buffer.from(account.access_token.split(".")[1], "base64").toString()
          );
          token.roles = payload?.realm_access?.roles ?? [];
        } catch {
          token.roles = [];
        }
      }
      return token;
    },
    async session({ session, token }) {
      // @ts-expect-error augmenting session
      session.accessToken = token.accessToken;
      // @ts-expect-error augmenting session
      session.roles = token.roles ?? [];
      return session;
    },
  },
  trustHost: true,
});
