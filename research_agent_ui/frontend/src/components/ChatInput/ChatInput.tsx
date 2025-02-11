// import React from 'react';
// import { ChatMode } from '../../types/chat';
// import { ChatInputCustom } from './ChatInputCustom';
// import { ChatInputResearch } from './ChatInputResearch';

// interface ChatInputProps {
//   mode: ChatMode;
//   onSubmit: (message: string, urls?: string[]) => void;
//   isLoading: boolean;
//   disabled?: boolean;
// }

// export const ChatInput: React.FC<ChatInputProps> = ({ mode, onSubmit, isLoading, disabled }) => {
//   if (!mode) return null;
  
//   return mode === 'custom' ? (
//     <ChatInputCustom
//       onSubmit={(message) => onSubmit(message)}
//       isLoading={isLoading}
//       disabled={disabled}
//     />
//   ) : (
//     <ChatInputResearch
//       onSubmit={onSubmit}
//       isLoading={isLoading}
//       disabled={disabled}
//     />
//   );
// };


import React from 'react';
import { ChatMode } from '../../types/chat';
import { ChatInputCustom } from './ChatInputCustom';
import { ChatInputResearch } from './ChatInputResearch';

interface ChatInputProps {
  mode: ChatMode;
  onSubmit: (message: string, urls?: string[]) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ mode, onSubmit, isLoading, disabled }) => {
  console.log('ChatInput - Current mode:', mode); // Debug log
  
  if (mode === 'custom') {
    return (
      <ChatInputCustom
        onSubmit={(message, file) => {
          console.log('ChatInputCustom - Submitting:', message, file); // Debug log
          onSubmit(message, file);
        }}
        isLoading={isLoading}
        disabled={disabled}
      />
    );
  }

  return (
    <ChatInputResearch
      onSubmit={onSubmit}
      isLoading={isLoading}
      disabled={disabled}
    />
  );
};