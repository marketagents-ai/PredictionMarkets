import React, { useState } from 'react';
import { ChatHistory } from '../ChatHistory';
import { ChatInputResearch } from '../ChatInput/ChatInputResearch';
import { useSystem } from '../../hooks/useSystem';
import { useCustomTools } from '../../hooks/useCustomTools';
import { ChatItem } from '../../types/chat';

export const ResearchMode: React.FC = () => {
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { activeMessage } = useSystem();
  const { tools } = useCustomTools();

  const handleSubmit = async (query: string) => {
    setIsLoading(true);
    try {
      // Filter and format enabled tools
      const enabledSchemas = tools
        .filter(tool => tool.enabled)
        .map(tool => ({
          name: tool.name,
          description: tool.description,
          schema_definition: {
            type: 'object',
            properties: {
              [tool.name]: {
                type: 'string',
                description: `Analysis and insights related to ${tool.name} in financial markets`
              },
              ...tool.schema.properties
            }
          }
        }));

      console.log('Enabled schemas for request:', enabledSchemas);

      const requestBody = {
        query,
        custom_schemas: enabledSchemas
      };

      console.log('Full request body:', JSON.stringify(requestBody, null, 2));

      const response = await fetch('http://localhost:8000/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Server error:', errorData);
        throw new Error(`Research request failed: ${errorData.detail}`);
      }

      const data = await response.json();
      console.log('Response from server:', data);

      setMessages(prev => [
        ...prev,
        {
          isUser: true,
          content: query,
          timestamp: new Date(),
          customSchemas: enabledSchemas
        },
        {
          isUser: false,
          content: data,
          timestamp: new Date(),
          customSchemas: enabledSchemas
        }
      ]);

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        {
          isUser: false,
          content: 'An error occurred while processing your request.',
          timestamp: new Date(),
          error: true
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        <ChatHistory messages={messages} />
      </div>
      <div className="border-t border-gray-800 p-4">
        <ChatInputResearch
          onSubmit={handleSubmit}
          isLoading={isLoading}
          disabled={!activeMessage}
        />
      </div>
    </div>
  );
};