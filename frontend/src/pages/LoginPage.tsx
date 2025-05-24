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
    const [email, setEmail] = useState('dad@example.com'); // Pre-filled for easier testing if desired
    const [password, setPassword] = useState('string'); // Pre-filled for easier testing
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();

    const from = location.state?.from?.pathname || "/dashboard"; // Changed default to /dashboard

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setIsLoading(true);
      setError(null);

      try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await apiClient.post('/login/access-token', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
        
        const { access_token } = response.data;

        const userProfileResponse = await apiClient.get('/users/me', {
            headers: { Authorization: `Bearer ${access_token}` }
        });

        login(access_token, userProfileResponse.data);
        
        navigate(from, { replace: true });
      } catch (err: any) {
        console.error("Login failed:", err);
        if (err.response && err.response.data && err.response.data.detail) {
          if (typeof err.response.data.detail === 'string') {
            setError(err.response.data.detail);
          } else if (Array.isArray(err.response.data.detail) && err.response.data.detail.length > 0 && err.response.data.detail[0].msg) {
            setError(err.response.data.detail[0].msg); // Handle Pydantic validation error structure
          } else {
            setError('An unexpected error format occurred.');
          }
        } else {
          setError('Login failed. Please check your credentials or network and try again.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4"> {/* Changed bg for better contrast from card */}
        <Card className="w-full max-w-sm shadow-lg"> {/* Added shadow */}
          <CardHeader className="text-center"> {/* Centered header text */}
            <CardTitle className="text-3xl font-bold">Login</CardTitle> {/* Made title larger and bolder */}
            <CardDescription className="pt-1"> {/* Added padding-top to description */}
              Enter your email below to login to your account.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6"> {/* Changed to space-y-6 for more vertical spacing */}
              <div className="space-y-2"> {/* Use space-y for inner elements */}
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
              <div className="space-y-2"> {/* Use space-y for inner elements */}
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
              {error && (
                <p className="text-sm text-destructive text-center px-1 py-2 bg-destructive/10 rounded-md"> {/* Styled error message */}
                    {error}
                </p>
              )}
            </CardContent>
            <CardFooter className="flex flex-col pt-2"> {/* Use flex-col for footer elements, reduced pt */}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Logging in...' : 'Login'}
              </Button>
              {/* You can add links like "Forgot password?" or "Sign up" here if needed */}
              {/* <div className="mt-4 text-center text-sm">
                Don't have an account?{' '}
                <Link to="/signup" className="underline">
                  Sign up
                </Link>
              </div> */}
            </CardFooter>
          </form>
        </Card>
      </div>
    );
  };

  export default LoginPage;