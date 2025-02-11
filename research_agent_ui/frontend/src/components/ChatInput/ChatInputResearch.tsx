import React, { useState } from 'react';
import { Send, Link } from 'lucide-react';

interface ChatInputResearchProps {
  onSubmit: (query: string, urls?: string[]) => void;  // Note: this accepts urls parameter
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInputResearch: React.FC<ChatInputResearchProps> = ({ 
  onSubmit, 
  isLoading, 
  disabled 
}) => {
  const [query, setQuery] = useState('');
  const [urls, setUrls] = useState('');
  const [showUrlInput, setShowUrlInput] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading && !disabled) {
      const urlList = urls.split('\n').filter(url => url.trim());
      onSubmit(query, urlList.length > 0 ? urlList : undefined);  // Here's where the query is sent
      setQuery('');
      setUrls('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your research query..."
            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading || disabled}
          />
          <button
            type="button"
            onClick={() => setShowUrlInput(!showUrlInput)}
            className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white transition-colors"
          >
            <Link size={20} />
          </button>
          <button
            type="submit"
            disabled={isLoading || disabled || !query.trim()}
            className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Send size={20} />
          </button>
        </div>

        {showUrlInput && (
          <textarea
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            placeholder="Enter URLs to research (one per line)"
            className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 h-24 resize-none"
            disabled={isLoading || disabled}
          />
        )}
      </div>
    </form>
  );
};