// src/pages/LoginPage.tsx
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import apiClient from '@/services/apiClient'; // Our API client
import { useAuth } from '@/contexts/AuthContext'; // Our Auth context

const LoginPage = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();

    // Get the path the user was trying to access before being redirected to login
    const from = location.state?.from?.pathname || "/";

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setIsLoading(true);
      setError(null);

      try {
        // FastAPI's OAuth2PasswordRequestForm expects x-www-form-urlencoded
        const formData = new URLSearchParams();
        formData.append('username', email); // 'username' is the field FastAPI expects for email
        formData.append('password', password);

        const response = await apiClient.post('/login/access-token', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
        
        const { access_token } = response.data; // This is our schemas.Token

        // We need user data. Let's fetch /users/me with the new token.
        const userProfileResponse = await apiClient.get('/users/me', {
            headers: { Authorization: `Bearer ${access_token}` }
        });

        login(access_token, userProfileResponse.data); // Pass token and user data to auth context
        
        navigate(from, { replace: true }); // Redirect to original intended page or dashboard
      } catch (err: any) {
        console.error("Login failed:", err);
        if (err.response && err.response.data && err.response.data.detail) {
          setError(err.response.data.detail);
        } else {
          setError('Login failed. Please check your credentials and try again.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <div className="flex items-center justify-center min-h-screen bg-muted/40 p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="text-2xl">Login</CardTitle>
            <CardDescription>
              Enter your email below to login to your account.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
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
              <div className="grid gap-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Logging in...' : 'Login'}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    );
  };

  export default LoginPage;