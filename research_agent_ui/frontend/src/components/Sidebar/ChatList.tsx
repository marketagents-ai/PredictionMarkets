import React from 'react';
import { MessageSquare } from 'lucide-react';
import type { Chat } from '../../types/chat';

interface ChatListProps {
  chats: Chat[];
  activeChat: string | null;
  onSelectChat: (chatId: string) => void;
}

export const ChatList: React.FC<ChatListProps> = ({ chats, activeChat, onSelectChat }) => {
  return (
    <div className="flex-1 overflow-y-auto">
      {chats.map((chat) => (
        <button
          key={chat.id}
          onClick={() => onSelectChat(chat.id)}
          className={`w-full text-left p-3 hover:bg-gray-700 flex items-center gap-2 ${
            activeChat === chat.id ? 'bg-gray-700' : ''
          }`}
        >
          <MessageSquare size={18} />
          <span className="truncate">{chat.title || 'New Chat'}</span>
        </button>
      ))}
    </div>
  );
};