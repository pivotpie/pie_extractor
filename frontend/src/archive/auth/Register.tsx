import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Building, Users, Zap, Github, CheckCircle, ArrowRight, Trophy, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import AppHeader from "@/components/AppHeader";
import { useSignUp } from "@clerk/clerk-react";

const Register = () => {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
    agreeToTerms: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"github" | "google" | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { isLoaded, signUp } = useSignUp();

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast({
        title: "Password Mismatch",
        description: "Passwords do not match. Please try again.",
        variant: "destructive",
      });
      return;
    }

    if (!formData.agreeToTerms) {
      toast({
        title: "Terms Required",
        description: "Please agree to the Terms of Service and Privacy Policy.",
        variant: "destructive",
      });
      return;
    }

    if (!isLoaded) {
      toast({
        title: "Error",
        description: "Authentication service is not ready. Please try again.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);

    try {
      await signUp.create({
        emailAddress: formData.email,
        password: formData.password,
        firstName: formData.full_name.split(' ')[0],
        lastName: formData.full_name.split(' ').slice(1).join(' ') || 'User',
      });

      // Send email verification code
      await signUp.prepareEmailAddressVerification({
        strategy: 'email_code',
      });

      // Show success message and redirect to verification page
      toast({
        title: "Check your email!",
        description: "We've sent a verification link to your email. Please verify your email to continue.",
      });
      
      // Redirect to verification page
      navigate('/verify-email');
    } catch (error) {
      console.error('Registration error:', error);
      toast({
        title: "Registration Failed",
        description: "There was an error creating your account. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'github' | 'google') => {
    if (!isLoaded) {
      toast({
        title: "Error",
        description: "Authentication service is not ready. Please try again.",
        variant: "destructive",
      });
      return;
    }

    setSocialLoading(provider);
    
    try {
      // Set up the redirect URL for the SSO callback
      const redirectUrl = new URL('/sso-callback', window.location.origin);
      
      // Start the OAuth flow with the provider
      await signUp.authenticateWithRedirect({
        strategy: `oauth_${provider}`,
        redirectUrl: redirectUrl.toString(),
        redirectUrlComplete: '/',
      });
    } catch (error) {
      console.error(`${provider} sign up error:`, error);
      toast({
        title: "Sign Up Failed",
        description: `Failed to sign up with ${provider}. Please try again.`,
        variant: "destructive",
      });
      setSocialLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted to-secondary/30">
      <div className="container mx-auto px-4 py-8 max-w-none">
        <AppHeader 
          title="Pie-Extractor"
          subtitle="Intelligent Data Extraction"
          logoSize="large"
          className="mb-8"
        />

        <div className="flex flex-col lg:flex-row gap-12 items-start max-w-6xl mx-auto">
          {/* Left side - Value Proposition */}
          <div className="flex-1 space-y-8">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 bg-success/10 text-success px-3 py-1 rounded-full text-sm font-medium">
                <Trophy className="h-4 w-4" />
                #1 AI Document Processing Platform
              </div>
              <h1 className="text-5xl font-bold leading-tight">
                Start Processing Documents
                <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent"> Intelligently</span>
              </h1>
              <p className="text-xl text-muted-foreground leading-relaxed">
                Join 10,000+ companies using Pie-Extractor to automate their data extraction workflows.
                Get started with our free tier and scale as you grow.
              </p>
            </div>

            {/* Key Benefits */}
            <div className="space-y-4">
              {[
                "Free forever plan - no credit card required",
                "Setup in under 2 minutes",
                "Enterprise-grade security from day one"
              ].map((benefit, index) => (
                <div key={index} className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-success" />
                  <span className="font-medium">{benefit}</span>
                </div>
              ))}
            </div>

            {/* Features */}
            <div className="grid gap-6">
              {[
                {
                  title: "Free Tier Includes",
                  description: "Perfect for getting started",
                  icon: <Zap className="h-6 w-6 text-primary" />,
                  features: [
                    "100 documents/month",
                    "Advanced OCR",
                    "API access",
                    "Email support"
                  ]
                },
                {
                  title: "Enterprise Security",
                  description: "Built for mission-critical workloads",
                  icon: <Building className="h-6 w-6 text-accent" />,
                  features: [
                    "SOC 2 Type II",
                    "HIPAA compliant",
                    "99.9% uptime SLA",
                    "24/7 support"
                  ]
                },
                {
                  title: "Team Collaboration",
                  description: "Scale with your organization",
                  icon: <Users className="h-6 w-6 text-success" />,
                  features: [
                    "Role permissions",
                    "Workflow automation",
                    "Real-time sync",
                    "Advanced analytics"
                  ]
                }
              ].map((feature, index) => (
                <div key={index} className="bg-card border rounded-lg p-6 shadow-sm">
                  <div className="flex items-center gap-4 mb-4">
                    <div className={`p-3 rounded-lg ${
                      index === 0 ? 'bg-primary/10' : 
                      index === 1 ? 'bg-accent/10' : 'bg-success/10'
                    }`}>
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {feature.features.map((item, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-success" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="bg-gradient-to-r from-primary/10 to-accent/10 border border-primary/20 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg mb-1">Ready to get started?</h3>
                  <p className="text-sm text-muted-foreground">No credit card required • Free forever</p>
                </div>
                <ArrowRight className="h-5 w-5 text-primary" />
              </div>
            </div>
          </div>

          {/* Right side - Registration Form */}
          <div className="w-full max-w-md">
            <Card className="border-border/50 shadow-xl backdrop-blur-sm bg-card/95">
              <CardHeader className="space-y-2">
                <CardTitle className="text-2xl font-bold">Create Your Account</CardTitle>
                <CardDescription>
                  Start processing documents intelligently in under 2 minutes
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Social Login Buttons */}
                <div className="space-y-3">
                  <Button 
                    variant="outline" 
                    className="w-full flex items-center gap-2"
                    onClick={() => handleSocialLogin("github")}
                    disabled={isLoading || socialLoading === 'github'}
                  >
                    {socialLoading === 'github' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Github className="h-4 w-4" />
                    )}
                    Sign up with GitHub
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full flex items-center gap-2"
                    onClick={() => handleSocialLogin("google")}
                    disabled={isLoading || socialLoading === 'google'}
                  >
                    {socialLoading === 'google' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
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
                    )}
                    Sign up with Google
                  </Button>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <Separator className="w-full" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Or sign up with email</span>
                  </div>
                </div>

                {/* Registration Form */}
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input 
                      id="full_name" 
                      placeholder="John Doe" 
                      required 
                      value={formData.full_name}
                      onChange={(e) => handleInputChange("full_name", e.target.value)}
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Work Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="john@company.com"
                      value={formData.email}
                      onChange={(e) => handleInputChange("email", e.target.value)}
                      required
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="Create a strong password"
                      value={formData.password}
                      onChange={(e) => handleInputChange("password", e.target.value)}
                      required
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder="Confirm your password"
                      value={formData.confirmPassword}
                      onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
                      required
                      className="h-11 transition-all duration-200 focus:shadow-md"
                    />
                  </div>

                  <div className="flex items-start space-x-2 pt-2">
                    <Checkbox
                      id="terms"
                      checked={formData.agreeToTerms}
                      onCheckedChange={(checked) => handleInputChange("agreeToTerms", checked as boolean)}
                      className="mt-1"
                    />
                    <div className="grid gap-1.5 leading-none">
                      <Label htmlFor="terms" className="text-sm leading-relaxed">
                        I agree to the{" "}
                        <Link to="/terms" className="text-primary hover:underline">
                          Terms of Service
                        </Link>{" "}
                        and{" "}
                        <Link to="/privacy" className="text-primary hover:underline">
                          Privacy Policy
                        </Link>
                      </Label>
                    </div>
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full h-11 text-base"
                    disabled={isLoading || socialLoading !== null}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating account...
                      </>
                    ) : (
                      "Create Account"
                    )}
                  </Button>
                </form>
                
                <div className="text-center text-sm text-muted-foreground">
                  Already have an account?{" "}
                  <Link to="/login" className="text-primary hover:underline font-medium">
                    Sign in here
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
