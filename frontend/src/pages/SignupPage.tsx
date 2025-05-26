// src/pages/SignupPage.tsx
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import apiClient from '@/services/apiClient';
import { toast } from 'sonner';
// import { useAuth } from '@/contexts/AuthContext'; // Optional: if auto-login after signup

const SignupPage = () => {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    
    const navigate = useNavigate();
    // const { login } = useAuth(); // Optional: if you want to auto-login

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);

      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters long.");
        return;
      }

      setIsLoading(true);

      try {
        const payload = {
          email: email,
          password: password,
          full_name: fullName || undefined, // Send undefined if empty, backend handles Optional
        };

        await apiClient.post('/users/', payload);
        
        toast.success("Account created successfully! Please log in.");
        navigate('/login');

        // Optional: Auto-login the user (more complex, requires fetching token after user creation)
        // For simplicity, we'll redirect to login first.
        // If implementing auto-login:
        // const loginPayload = new URLSearchParams();
        // loginPayload.append('username', email);
        // loginPayload.append('password', password);
        // const tokenResponse = await apiClient.post('/login/access-token', loginPayload, { /* headers */ });
        // const userProfileResponse = await apiClient.get('/users/me', { headers: { Authorization: `Bearer ${tokenResponse.data.access_token}` } });
        // login(tokenResponse.data.access_token, userProfileResponse.data);
        // navigate('/dashboard'); // Or wherever new users should go

      } catch (err: any) {
        console.error("Signup failed:", err);
        if (err.response && err.response.data && err.response.data.detail) {
          if (typeof err.response.data.detail === 'string') {
            setError(err.response.data.detail);
          } else if (Array.isArray(err.response.data.detail) && err.response.data.detail.length > 0 && err.response.data.detail[0].msg) {
            setError(err.response.data.detail[0].msg);
          } else {
            setError('An unexpected error format occurred.');
          }
        } else {
          setError('Signup failed. Please try again.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
        <Card className="w-full max-w-md shadow-lg"> {/* Slightly wider card for more fields */}
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold">Create Account</CardTitle>
            <CardDescription className="pt-1">
              Enter your details to create a new account.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4"> {/* Adjusted spacing */}
              <div className="space-y-1.5">
                <Label htmlFor="fullName">Full Name (Optional)</Label>
                <Input
                  id="fullName"
                  type="text"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="m@example.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  placeholder="********"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
                 <p className="text-xs text-muted-foreground">Must be at least 8 characters.</p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  required
                  placeholder="********"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              {error && (
                <p className="text-sm text-destructive text-center px-1 py-2 bg-destructive/10 rounded-md">
                    {error}
                </p>
              )}
            </CardContent>
            <CardFooter className="flex flex-col pt-4 gap-3"> {/* Added gap */}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </Button>
              <div className="text-center text-sm">
                Already have an account?{' '}
                <Link to="/login" className="underline hover:text-primary">
                  Log In
                </Link>
              </div>
            </CardFooter>
          </form>
        </Card>
      </div>
    );
  };

  export default SignupPage;