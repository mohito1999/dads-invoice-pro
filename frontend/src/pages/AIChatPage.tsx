// src/pages/AIChatPage.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area"; // You might need to add this: npx shadcn-ui@latest add scroll-area
import apiClient from '@/services/apiClient'; // Your API client
import { useAuth } from '@/contexts/AuthContext'; // To ensure user is authenticated
import { SendHorizonalIcon } from 'lucide-react'; // Icon for send button
import { toast } from 'sonner'; // For error notifications

interface ChatMessage {
    role: 'user' | 'model' | 'function_call_request' | 'function_call_response' | 'system_error'; // Match your history structure
    parts: any[]; // For simplicity, 'any[]'. Could be string[] or more specific later.
}

const AIChatPage = () => {
    const { token } = useAuth(); // Get token for API calls
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [currentMessage, setCurrentMessage] = useState('');
    const [isLoadingAI, setIsLoadingAI] = useState(false);
    const scrollAreaRef = useRef<HTMLDivElement>(null); // For auto-scrolling

    // Auto-scroll to bottom when new messages are added
    useEffect(() => {
        if (scrollAreaRef.current) {
            const scrollViewport = scrollAreaRef.current.querySelector('div[data-radix-scroll-area-viewport]');
            if (scrollViewport) {
                scrollViewport.scrollTop = scrollViewport.scrollHeight;
            }
        }
    }, [messages]);

    const handleSendMessage = async (e?: React.FormEvent<HTMLFormElement>) => {
        if (e) e.preventDefault();
        if (!currentMessage.trim() || isLoadingAI) return;

        const userMessage: ChatMessage = { role: 'user', parts: [currentMessage.trim()] };
        
        // Add user message to local state immediately for responsiveness
        const newMessagesWithUser = [...messages, userMessage];
        setMessages(newMessagesWithUser);
        const messageToSendToAPI = currentMessage.trim();
        setCurrentMessage('');
        setIsLoadingAI(true);

        try {
            // Prepare history to send (all messages *before* the current user message)
            const historyForAPI = messages; // Send the state *before* adding the current user's message

            const response = await apiClient.post('/chat/', {
                message: messageToSendToAPI,
                history: historyForAPI, // Send history up to the point *before* this user message
            }
            // No explicit token needed here if apiClient interceptor handles it
            );

            const { reply, history: updatedHistoryFromServer, follow_up_question } = response.data;
            
            // The backend now returns the *complete* updated history.
            // We can just set our messages state to this.
            setMessages(updatedHistoryFromServer);

            if (follow_up_question) {
                // Optionally display this in a different way or just let it be the AI's reply
                console.log("AI has a follow-up question:", follow_up_question);
            }

        } catch (error: any) {
            console.error("Error sending message to AI:", error);
            const errorMessage = error.response?.data?.detail || "Failed to get response from AI.";
            toast.error(errorMessage);
            // Add an error message to the chat display
            setMessages(prevMessages => [...prevMessages, {role: 'system_error', parts: [errorMessage]}]);
        } finally {
            setIsLoadingAI(false);
        }
    };
    
    // Helper to render message parts (assuming parts are strings for now)
    const renderMessagePart = (part: any, index: number) => {
        if (typeof part === 'string') {
            return <span key={index}>{part}</span>;
        }
        if (typeof part === 'object' && part !== null) {
            if (part.text) return <span key={index}>{part.text}</span>;
            if (part.name && part.args) { // function_call_request
                return <pre key={index} className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded-md overflow-x-auto">Tool Call Request: {part.name}({JSON.stringify(part.args, null, 2)})</pre>;
            }
            if (part.name && part.response) { // function_call_response
                 return <pre key={index} className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded-md overflow-x-auto">Tool Result ({part.name}): {JSON.stringify(part.response, null, 2)}</pre>;
            }
        }
        return <span key={index}>{JSON.stringify(part)}</span>; // Fallback
    };


    if (!token) {
        return <div className="p-4 text-center">Please log in to use the AI Chat.</div>;
    }

    return (
        <div className="flex flex-col h-[calc(100vh-120px)] max-w-3xl mx-auto border rounded-lg shadow-sm"> {/* Adjust height as needed */}
            <div className="p-4 border-b">
                <h2 className="text-xl font-semibold">ProVoice AI Assistant</h2>
            </div>

            <ScrollArea className="flex-grow p-4 space-y-4" ref={scrollAreaRef}>
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`flex ${
                            msg.role === 'user' ? 'justify-end' : 'justify-start'
                        }`}
                    >
                        <div
                            className={`max-w-[70%] p-3 rounded-lg shadow ${
                                msg.role === 'user'
                                    ? 'bg-primary text-primary-foreground'
                                    : msg.role === 'system_error'
                                    ? 'bg-destructive text-destructive-foreground'
                                    : 'bg-muted' 
                            }`}
                        >
                           {msg.parts.map((part, partIndex) => renderMessagePart(part, partIndex))}
                        </div>
                    </div>
                ))}
                {isLoadingAI && (
                     <div className="flex justify-start">
                        <div className="max-w-[70%] p-3 rounded-lg shadow bg-muted">
                            <span className="italic text-gray-500">AI is thinking...</span>
                        </div>
                    </div>
                )}
            </ScrollArea>

            <div className="p-4 border-t">
                <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
                    <Input
                        type="text"
                        placeholder="Ask ProVoice AI anything about your invoices..."
                        value={currentMessage}
                        onChange={(e) => setCurrentMessage(e.target.value)}
                        disabled={isLoadingAI}
                        className="flex-grow"
                    />
                    <Button type="submit" disabled={isLoadingAI || !currentMessage.trim()} size="icon">
                        <SendHorizonalIcon className="h-5 w-5" />
                    </Button>
                </form>
            </div>
        </div>
    );
};

export default AIChatPage;