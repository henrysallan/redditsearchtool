import React, { useState, useEffect } from 'react';

interface ProgressStep {
  id: string;
  message: string;
  duration: number; // How long to show this step in ms
  delay?: number; // Delay before showing this step
}

interface SearchProgressConsoleProps {
  isVisible: boolean;
  searchQuery: string;
  maxPosts: number;
}

export const SearchProgressConsole: React.FC<SearchProgressConsoleProps> = ({
  isVisible,
  searchQuery,
  maxPosts
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [visibleSteps, setVisibleSteps] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  // Define the progress steps that mirror our backend process
  const progressSteps: ProgressStep[] = [
    {
      id: 'init',
      message: '🚀 Initializing search system...',
      duration: 800
    },
    {
      id: 'google_search',
      message: `🔍 Searching Google for Reddit posts about "${searchQuery}"...`,
      duration: 1200
    },
    {
      id: 'reddit_urls',
      message: `📋 Found Reddit discussions, processing ${maxPosts} most relevant posts...`,
      duration: 1000
    },
    {
      id: 'reddit_data',
      message: '📖 Extracting post content and top comments...',
      duration: 1500
    },
    {
      id: 'analytics',
      message: '📊 Analyzing engagement metrics and community insights...',
      duration: 1000
    },
    {
      id: 'ai_summary',
      message: '🤖 Generating comprehensive AI summary...',
      duration: 2000
    },
    {
      id: 'extract_terms',
      message: '🔤 Extracting key search terms from discussion...',
      duration: 800
    },
    {
      id: 'enhanced_search',
      message: '🌐 Finding enhanced external resources...',
      duration: 1200
    },
    {
      id: 'ai_curation',
      message: '✨ AI-curating the most valuable links...',
      duration: 1000
    },
    {
      id: 'complete',
      message: '✅ Search completed successfully!',
      duration: 500
    }
  ];

  // Reset when search starts
  useEffect(() => {
    if (isVisible) {
      setCurrentStep(0);
      setVisibleSteps([]);
      setIsComplete(false);
    }
  }, [isVisible]);

  // Progress through steps
  useEffect(() => {
    if (!isVisible || isComplete) return;

    if (currentStep < progressSteps.length) {
      const step = progressSteps[currentStep];
      
      // Add current step to visible steps
      const timer = setTimeout(() => {
        setVisibleSteps(prev => [...prev, step.id]);
        
        // Move to next step after duration
        setTimeout(() => {
          if (currentStep === progressSteps.length - 1) {
            setIsComplete(true);
          } else {
            setCurrentStep(prev => prev + 1);
          }
        }, step.duration);
      }, step.delay || 0);

      return () => clearTimeout(timer);
    }
  }, [currentStep, isVisible, isComplete, progressSteps.length]);

  // Calculate progress percentage
  const progress = (visibleSteps.length / progressSteps.length) * 100;

  if (!isVisible) return null;

  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-4xl">
        {/* Minimal Progress Console */}
        <div 
          className="bg-white text-black overflow-hidden"
          style={{ 
            border: '3px solid #000000'
          }}
        >
          {/* Header */}
          <div className="px-6 py-4" style={{ borderBottom: '3px solid #000000' }}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Searching Reddit</h3>
              <div className="text-sm text-gray-600">
                "{searchQuery}" • {maxPosts} posts
              </div>
            </div>
          </div>

          {/* Progress Content */}
          <div className="p-6">
            <div className="space-y-3 mb-6">
              {visibleSteps.map((stepId, index) => {
                const step = progressSteps.find(s => s.id === stepId);
                if (!step) return null;
                
                return (
                  <div
                    key={step.id}
                    className={`transition-all duration-500 ${
                      index === visibleSteps.length - 1 
                        ? 'opacity-100 font-medium' 
                        : 'opacity-60'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">
                        {index === visibleSteps.length - 1 ? '▶' : '✓'}
                      </span>
                      <span>{step.message}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Progress</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-gray-200 h-3" style={{ border: '2px solid #000000' }}>
                <div 
                  className="bg-black h-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};