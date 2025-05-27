// src/pages/AIChatPage.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import apiClient from '@/services/apiClient';
import { useAuth } from '@/contexts/AuthContext';
import { SendHorizonalIcon, BotIcon, UserIcon, AlertCircleIcon, MessageSquarePlusIcon } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';

interface ChatMessagePart {
    text?: string;
    name?: string; 
    args?: Record<string, any>;
    response?: Record<string, any>;
}
interface ChatMessage {
    role: 'user' | 'model' | 'function_call_request' | 'function_call_response' | 'system_error';
    parts: ChatMessagePart[] | string[]; 
}

const AIChatPage = () => {
    const { token } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]); // Initialize with empty messages
    const [currentMessage, setCurrentMessage] = useState('');
    const [isLoadingAI, setIsLoadingAI] = useState(false);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // REMOVED: useEffect that set the initial AI welcome message into `messages` state.

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoadingAI]);

    const handleSendMessage = async (e?: React.FormEvent<HTMLFormElement>) => {
        if (e) e.preventDefault();
        if (!currentMessage.trim() || isLoadingAI) return;

        const userTypedMessage = currentMessage.trim();
        const userMessageForState: ChatMessage = { role: 'user', parts: [{text: userTypedMessage}] };
        
        // Add user's message to the *current* set of messages for UI update
        // The history sent to API will be based on the state *before* this new user message
        const historyForAPI = [...messages]; // Capture current messages as history
        setMessages(prevMessages => [...prevMessages, userMessageForState]); // Update UI

        setCurrentMessage('');
        setIsLoadingAI(true);

        try {
            const response = await apiClient.post('/chat/', {
                message: userTypedMessage,
                history: historyForAPI, // Send the captured history
            });

            const { history: updatedHistoryFromServer } = response.data;
            // The server returns the full history including the latest user message and AI response(s)
            setMessages(updatedHistoryFromServer);

        } catch (error: any) {
            console.error("Error sending message to AI:", error);
            const errorMessage = error.response?.data?.detail || "Failed to get response from AI. Please try again.";
            toast.error(errorMessage);
            // Add error to UI, it will be part of the `messages` state
            setMessages(prevMessages => [...prevMessages, {role: 'system_error', parts: [{text: errorMessage}]}]);
        } finally {
            setIsLoadingAI(false);
        }
    };
    
    const renderMessageContent = (msg: ChatMessage, msgIndex: number) => {
        if (msg.role === 'user' || msg.role === 'model' || msg.role === 'system_error') {
            const partsToRender = Array.isArray(msg.parts) 
                ? msg.parts.map(part => typeof part === 'string' ? { text: part } : part) 
                : [{ text: '' }]; 

            return partsToRender.map((part, partIndex) => {
                const partContent = part.text || '';
                return partContent.split('\n').map((line, lineIdx) => (
                    <React.Fragment key={`${msgIndex}-${partIndex}-${lineIdx}`}>
                        {line}
                        {lineIdx < partContent.split('\n').length - 1 && <br />}
                    </React.Fragment>
                ));
            });
        }
        return null;
    };

    if (!token) {
        return (
            <div className="container mx-auto max-w-screen-lg px-4 py-8 text-center">
                <AlertCircleIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-xl text-muted-foreground">Please log in to use the AI Chat Assistant.</p>
            </div>
        );
    }

    const aiWelcomeMessage = `Hello! I'm ProVoice AI, your expert assistant for ProVoice. I'm here to help you manage your invoicing tasks. How can I assist you today?`;

    return (
        <div className="container mx-auto max-w-screen-lg px-4 py-8 sm:px-6 lg:px-8 space-y-6">
            {/* Page Header */}
            <div className="flex flex-col items-start gap-1">
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center">
                    <BotIcon className="mr-3 h-8 w-8 text-primary shrink-0" />
                    ProVoice AI Assistant
                </h1>
                <p className="text-muted-foreground">
                    Chat with your AI assistant to manage customers, items, and invoices.
                </p>
            </div>

            {/* Chat Area Card */}
            <Card className="w-full flex flex-col shadow-xl h-[calc(100vh-18rem)]">
                <CardContent className="p-0 flex-grow flex flex-col">
                    <ScrollArea className="flex-grow h-0">
                        <div className="p-4 sm:p-6 space-y-4">
                            {/* Static Welcome Message - UI Only */}
                            <div
                                className={cn(
                                    "flex items-end gap-2.5 justify-start mr-auto"
                                )}
                            >
                                <div className="flex-shrink-0 bg-primary text-primary-foreground rounded-full h-9 w-9 flex items-center justify-center shadow">
                                    <BotIcon className="h-5 w-5" />
                                </div>
                                <div
                                    className={cn(
                                        "max-w-[75%] sm:max-w-[70%] p-3 px-4 rounded-2xl shadow-md text-sm sm:text-base leading-relaxed break-words", 
                                        'bg-muted dark:bg-slate-800 rounded-bl-md'
                                    )}
                                >
                                {aiWelcomeMessage.split('\n').map((line, lineIdx) => (
                                    <React.Fragment key={`welcome-${lineIdx}`}>
                                        {line}
                                        {lineIdx < aiWelcomeMessage.split('\n').length - 1 && <br />}
                                    </React.Fragment>
                                ))}
                                </div>
                            </div>

                            {/* Dynamically rendered messages from state */}
                            {messages.map((msg, index) => {
                                if (msg.role !== 'user' && msg.role !== 'model' && msg.role !== 'system_error') {
                                    return null; 
                                }
                                const isUser = msg.role === 'user';
                                const isError = msg.role === 'system_error';
                                return (
                                    <div
                                        key={index}
                                        className={cn(
                                            "flex items-end gap-2.5 animate-in fade-in slide-in-from-bottom-3 duration-300 ease-out",
                                            isUser ? 'justify-end ml-auto' : 'justify-start mr-auto'
                                        )}
                                    >
                                        {!isUser && !isError && (
                                            <div className="flex-shrink-0 bg-primary text-primary-foreground rounded-full h-9 w-9 flex items-center justify-center shadow">
                                                <BotIcon className="h-5 w-5" />
                                            </div>
                                        )}
                                        {!isUser && isError && (
                                            <div className="flex-shrink-0 bg-destructive text-destructive-foreground rounded-full h-9 w-9 flex items-center justify-center shadow">
                                                <AlertCircleIcon className="h-5 w-5" />
                                            </div>
                                        )}
                                        <div
                                            className={cn(
                                                "max-w-[75%] sm:max-w-[70%] p-3 px-4 rounded-2xl shadow-md text-sm sm:text-base leading-relaxed break-words", 
                                                isUser 
                                                    ? 'bg-primary text-primary-foreground rounded-br-md'
                                                    : isError 
                                                    ? 'bg-destructive/10 text-destructive-foreground border border-destructive/20 rounded-bl-md' 
                                                    : 'bg-muted dark:bg-slate-800 rounded-bl-md'
                                            )}
                                        >
                                        {renderMessageContent(msg, index)}
                                        </div>
                                        {isUser && (
                                            <div className="flex-shrink-0 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full h-9 w-9 flex items-center justify-center shadow">
                                                <UserIcon className="h-5 w-5" />
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                            {isLoadingAI && (
                                <div className="flex items-end gap-2.5 justify-start mr-auto">
                                    <div className="flex-shrink-0 bg-primary text-primary-foreground rounded-full h-9 w-9 flex items-center justify-center shadow">
                                        <BotIcon className="h-5 w-5" />
                                    </div>
                                    <div className="max-w-[70%] p-3 px-4 rounded-2xl shadow-md bg-muted dark:bg-slate-800 rounded-bl-md">
                                        <div className="flex items-center space-x-1.5 py-1.5">
                                            <span className="h-2.5 w-2.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                            <span className="h-2.5 w-2.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                            <span className="h-2.5 w-2.5 bg-slate-400 rounded-full animate-bounce"></span>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} className="h-1"></div>
                        </div>
                        <ScrollBar orientation="vertical" />
                    </ScrollArea>

                    <div className="p-3 sm:p-4 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                        <form onSubmit={handleSendMessage} className="flex items-center gap-2 sm:gap-3">
                            <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary shrink-0" onClick={() => setMessages([])} title="Clear Chat">
                                <MessageSquarePlusIcon className="h-5 w-5"/>
                            </Button>
                            <Input
                                type="text"
                                placeholder="Chat with ProVoice AI..."
                                value={currentMessage}
                                onChange={(e) => setCurrentMessage(e.target.value)}
                                disabled={isLoadingAI}
                                className="flex-grow h-11 text-base px-4"
                                onKeyPress={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey && !isLoadingAI && currentMessage.trim()) {
                                        e.preventDefault(); 
                                        handleSendMessage();
                                    }
                                }}
                            />
                            <Button type="submit" disabled={isLoadingAI || !currentMessage.trim()} size="lg" className="h-11 px-5 text-base">
                                <SendHorizonalIcon className="h-5 w-5 mr-0 sm:mr-2" />
                                <span className="hidden sm:inline">Send</span>
                            </Button>
                        </form>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default AIChatPage;