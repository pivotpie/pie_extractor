import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { FileText, Zap, Shield, Star, Users, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import AppHeader from '@/components/AppHeader';
import { useAuth } from '@/contexts/AuthContext';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast({
        title: 'Missing Information',
        description: 'Please enter both email and password.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    
    try {
      const success = await login({ email, password });
      
      if (success) {
        toast({
          title: 'Welcome to Pie-Extractor',
          description: 'Successfully logged in to your account.',
        });
        navigate('/');
      } else {
        throw new Error('Invalid credentials');
      }
    } catch (error) {
      toast({
        title: 'Login Failed',
        description: 'Invalid email or password. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
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
                <div className="relative py-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={isLoading}
                      autoComplete="email"
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="password">Password</Label>
                      <a href="#" className="text-sm font-medium text-primary hover:underline">
                        Forgot password?
                      </a>
                    </div>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={isLoading}
                      autoComplete="current-password"
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      'Sign In with Email'
                    )}
                  </Button>
                </form>
                <p className="mt-4 text-center text-sm text-muted-foreground">
                  Don't have an account?{' '}
                  <a href="#" className="font-medium text-primary hover:underline">
                    Contact Sales
                  </a>
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
