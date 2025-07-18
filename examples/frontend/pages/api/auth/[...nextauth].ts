import NextAuth, { NextAuthOptions } from "next-auth"
import { PrismaAdapter } from "@auth/prisma-adapter"
import { PrismaClient } from "@prisma/client"
import GitHubProvider from "next-auth/providers/github"
import GoogleProvider from "next-auth/providers/google"

const prisma = new PrismaClient()

// Validate required environment variables
const githubClientId = process.env.GITHUB_ID;
const githubClientSecret = process.env.GITHUB_SECRET;
const googleClientId = process.env.GOOGLE_CLIENT_ID;
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;

if (!githubClientId || !githubClientSecret) {
  console.warn('GitHub OAuth environment variables are missing. GitHub login will be disabled.');
}

if (!googleClientId || !googleClientSecret) {
  console.warn('Google OAuth environment variables are missing. Google login will be disabled.');
}

if (!githubClientId && !googleClientId) {
  throw new Error('At least one OAuth provider must be configured. Please check your .env.local file.');
}

export const authOptions: NextAuthOptions = {
  // Configure one or more authentication providers
  adapter: PrismaAdapter(prisma),
  providers: [
    ...(githubClientId && githubClientSecret ? [GitHubProvider({
      clientId: githubClientId,
      clientSecret: githubClientSecret,
    })] : []),
    ...(googleClientId && googleClientSecret ? [GoogleProvider({
      clientId: googleClientId,
      clientSecret: googleClientSecret,
    })] : []),
  ].filter(Boolean),
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/auth/signin",
    signOut: "/auth/signout",
    error: "/auth/error",
  },
  callbacks: {
    async session({ session, token }) {
      if (token?.sub) {
        session.user.id = token.sub
      }
      return session
    },
  },
  debug: process.env.NODE_ENV === "development",
}

export default NextAuth(authOptions)
