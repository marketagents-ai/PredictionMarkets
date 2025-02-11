import { useState, useEffect } from 'react';
import type { Chat, ChatItem, ChatMode } from '../types/chat';

export const useChats = () => {
  const [chats, setChats] = useState<Chat[]>(() => {
    const saved = localStorage.getItem('chats');
    return saved ? JSON.parse(saved) : [];
  });
  const [activeChat, setActiveChat] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem('chats', JSON.stringify(chats));
  }, [chats]);

  const createChat = (mode: ChatMode = 'research') => {
    const newChat: Chat = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      mode,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setChats(prev => [newChat, ...prev]);
    setActiveChat(newChat.id);
    return newChat.id;
  };

  const updateChat = (chatId: string, messages: ChatItem[]) => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        const firstMessage = messages[0]?.content;
        const title = typeof firstMessage === 'string' 
          ? firstMessage.slice(0, 30) 
          : 'Research Chat';
        
        return {
          ...chat,
          title,
          messages,
          updatedAt: new Date(),
        };
      }
      return chat;
    }));
  };

  const updateChatMode = (chatId: string, mode: ChatMode) => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        return {
          ...chat,
          mode,
          updatedAt: new Date(),
        };
      }
      return chat;
    }));
  };

  return {
    chats,
    activeChat,
    setActiveChat,
    createChat,
    updateChat,
    updateChatMode,
  };
};