import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { FileText, Zap, Shield, Github, Star, Users, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AppHeader from "@/components/AppHeader";
import { useSignIn } from "@clerk/clerk-react";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"github" | "google" | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { signIn, setActive, isLoaded } = useSignIn();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast({
        title: "Missing Information",
        description: "Please enter both email and password.",
        variant: "destructive",
      });
      return;
    }

    if (!isLoaded) {
      return;
    }

    setIsLoading(true);
    
    try {
      const result = await signIn.create({
        identifier: email,
        password,
      });

      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId });
        toast({
          title: "Welcome to Pie-Extractor",
          description: "Successfully logged in to your account.",
        });
        navigate("/documents");
      }
    } catch (err: any) {
      console.error('Login error:', err);
      toast({
        title: "Login Failed",
        description: err.errors?.[0]?.message || "Invalid email or password. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = (provider: 'github' | 'google') => {
    if (!isLoaded) return;
    
    signIn.authenticateWithRedirect({
      strategy: `oauth_${provider}`,
      redirectUrl: '/sso-callback',
      redirectUrlComplete: '/documents',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted to-secondary/30">
      {/* Header with branding */}
      <div className="container mx-auto px-4 py-8 max-w-none">
        <AppHeader 
          title="Pie-Extractor"
          subtitle="Intelligent Data Extraction"
          logoSize="large"
          className="mb-12"
        />

        <div className="flex flex-col lg:flex-row gap-12 items-center max-w-6xl mx-auto">
          {/* Left side - Enhanced Features showcase */}
          <div className="flex-1 space-y-8">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
                <Star className="h-4 w-4" />
                Trusted by 10,000+ businesses
              </div>
              <h1 className="text-5xl font-bold leading-tight">
                Transform Documents with 
                <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent"> AI Intelligence</span>
              </h1>
              <p className="text-xl text-muted-foreground leading-relaxed">
                Extract, analyze, and process documents 90% faster with our enterprise-grade AI platform. 
                Built for teams that handle thousands of documents monthly.
              </p>
            </div>

            {/* Stats Section */}
            <div className="grid grid-cols-3 gap-6 py-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">99.7%</div>
                <div className="text-sm text-muted-foreground">Accuracy Rate</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-accent">10M+</div>
                <div className="text-sm text-muted-foreground">Documents Processed</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-success">90%</div>
                <div className="text-sm text-muted-foreground">Time Saved</div>
              </div>
            </div>

            <div className="grid gap-6">
              <div className="flex items-start gap-4 p-4 rounded-lg bg-card/50 border border-border/50">
                <div className="bg-primary/10 p-3 rounded-lg">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Smart Data Extraction</h3>
                  <p className="text-muted-foreground">
                    OCR, classification, and data extraction from invoices, contracts, forms, and more.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 rounded-lg bg-card/50 border border-border/50">
                <div className="bg-accent/10 p-3 rounded-lg">
                  <Zap className="h-6 w-6 text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Lightning Fast Processing</h3>
                  <p className="text-muted-foreground">
                    Process 10,000+ documents per hour with 95%+ accuracy using advanced AI models.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 rounded-lg bg-card/50 border border-border/50">
                <div className="bg-success/10 p-3 rounded-lg">
                  <Shield className="h-6 w-6 text-success" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Enterprise Security</h3>
                  <p className="text-muted-foreground">
                    SOC 2, HIPAA, and GDPR compliant with end-to-end encryption.
                  </p>
                </div>
              </div>
            </div>

            {/* Social Proof */}
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>Join companies like Microsoft, Salesforce, and 10,000+ others</span>
            </div>
          </div>

          {/* Right side - Enhanced Login form */}
          <div className="w-full max-w-md">
            <Card className="border-border/50 shadow-xl backdrop-blur-sm bg-card/95">
              <CardHeader className="space-y-2">
                <CardTitle className="text-2xl font-bold">Welcome Back</CardTitle>
                <CardDescription>
                  Sign in to your Pie-Extractor dashboard and continue processing
                </CardDescription>
                <Button 
                  asChild
                  variant="outline" 
                  className="w-full flex items-center gap-2"
                >
                  <a href="/api/auth/github">
                    <Github className="h-4 w-4" />
                    Sign in with GitHub
                  </a>
                </Button>
                <Button 
                  asChild
                  variant="outline" 
                  className="w-full flex items-center gap-2"
                >
                  <a href="/api/auth/google">
                    <svg className="h-4 w-4" viewBox="0 0 24 24">
                      <path 
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" 
                        fill="#4285F4" 
                      />
                      <path 
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" 
                        fill="#34A853" 
                      />
                      <path 
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" 
                        fill="#FBBC05" 
                      />
                      <path 
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" 
                        fill="#EA4335" 
                      />
                    </svg>
                    Sign in with Google
                  </a>
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" 
                      fill="#34A853" 
                    />
                    <path 
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" 
                      fill="#FBBC05" 
                    />
                    <path 
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" 
                      fill="#EA4335" 
                    />
                  </svg>
                  {isLoading ? 'Redirecting...' : 'Sign in with Google'}
                </Button>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <Separator className="w-full" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Or continue with email</span>
                  </div>
                </div>

                {/* Email Login Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="password">Password</Label>
                      <Link to="/forgot-password" className="text-sm text-primary hover:underline">
                        Forgot?
                      </Link>
                    </div>
                    <Input
                      id="password"
                      type="password"
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>
                  <Button 
                    type="submit" 
                    className="w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      "Sign In"
                    )}
                    </a>
                  </Button>
                </form>
                
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">
                    Don't have an account?{" "}
                    <Link to="/register" className="text-primary hover:underline font-medium">
                      Sign up for free
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;