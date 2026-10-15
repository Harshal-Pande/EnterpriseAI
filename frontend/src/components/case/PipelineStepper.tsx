import React from 'react';
import { Check, X, Clock } from 'lucide-react';
import type { WorkflowStage } from '../../types';

export type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'awaiting';

export interface PipelineStep {
  id: string;
  stepNumber: number;
  title: string;
  status: StepStatus;
  statusText: string;
  timestamp?: string;
  targetSectionId?: string;
}

interface PipelineStepperProps {
  currentStage?: WorkflowStage;
  activeStepIndex?: number;
  onStepClick?: (step: PipelineStep) => void;
  className?: string;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  currentStage = 'IDLE',
  onStepClick,
  className = '',
}) => {
  // Map WorkflowStage to 7 fixed pipeline steps
  const deriveStepStatus = (stepIdx: number): { status: StepStatus; statusText: string } => {
    // Stage progress indices
    const stageMap: Record<WorkflowStage, number> = {
      IDLE: 0,
      RECEIVED: 1,
      SUPERVISOR_ANALYSIS: 2,
      INVENTORY_CHECK: 3,
      PROCUREMENT_NEGOTIATION: 3,
      FINANCE_VALIDATION: 3,
      LOGISTICS_FEASIBILITY: 3,
      SUPERVISOR_DECISION: 4,
      ORDER_FULFILLED: 6,
      COMPLETED: 7,
      EXCEPTION: 5,
    };

    const currentLevel = stageMap[currentStage] ?? 0;

    if (currentLevel > stepIdx) {
      return { status: 'done', statusText: 'Completed' };
    }
    if (currentLevel === stepIdx) {
      if (currentStage === 'EXCEPTION') {
        return { status: 'awaiting', statusText: 'Awaiting approval' };
      }
      return { status: 'running', statusText: 'In progress' };
    }
    return { status: 'pending', statusText: 'Pending' };
  };

  const steps: PipelineStep[] = [
    {
      id: 'scenario',
      stepNumber: 1,
      title: 'Scenario',
      ...deriveStepStatus(1),
      timestamp: '19:15:02',
      targetSectionId: 'section-scenario',
    },
    {
      id: 'supervisor',
      stepNumber: 2,
      title: 'Supervisor analysis',
      ...deriveStepStatus(2),
      timestamp: '19:15:03',
      targetSectionId: 'section-supervisor',
    },
    {
      id: 'specialists',
      stepNumber: 3,
      title: 'Specialist checks',
      ...deriveStepStatus(3),
      timestamp: '19:15:05',
      targetSectionId: 'section-specialists',
    },
    {
      id: 'policy',
      stepNumber: 4,
      title: 'Policy check',
      ...deriveStepStatus(4),
      timestamp: '19:15:06',
      targetSectionId: 'section-policy',
    },
    {
      id: 'governance',
      stepNumber: 5,
      title: 'Governance',
      ...deriveStepStatus(5),
      timestamp: '19:15:07',
      targetSectionId: 'section-governance',
    },
    {
      id: 'action',
      stepNumber: 6,
      title: 'Action',
      ...deriveStepStatus(6),
      timestamp: '19:15:08',
      targetSectionId: 'section-action',
    },
    {
      id: 'audit',
      stepNumber: 7,
      title: 'Audit',
      ...deriveStepStatus(7),
      timestamp: '19:15:09',
      targetSectionId: 'section-audit',
    },
  ];

  const handleStepClick = (step: PipelineStep) => {
    if (step.targetSectionId) {
      const el = document.getElementById(step.targetSectionId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
    onStepClick?.(step);
  };

  const renderStepIndicator = (step: PipelineStep) => {
    switch (step.status) {
      case 'done':
        return (
          <div className="w-6 h-6 rounded-full bg-ok text-white flex items-center justify-center shrink-0">
            <Check className="w-3.5 h-3.5" />
          </div>
        );
      case 'running':
        return (
          <div className="w-6 h-6 rounded-full bg-info text-white flex items-center justify-center font-mono text-[11px] font-semibold shrink-0 animate-step-pulse">
            {step.stepNumber}
          </div>
        );
      case 'failed':
        return (
          <div className="w-6 h-6 rounded-full bg-danger text-white flex items-center justify-center shrink-0">
            <X className="w-3.5 h-3.5" />
          </div>
        );
      case 'awaiting':
        return (
          <div className="w-6 h-6 rounded-full bg-warn text-white flex items-center justify-center shrink-0">
            <Clock className="w-3.5 h-3.5" />
          </div>
        );
      default:
        return (
          <div className="w-6 h-6 rounded-full bg-surface-2 text-text-3 border border-border flex items-center justify-center font-mono text-[11px] shrink-0">
            {step.stepNumber}
          </div>
        );
    }
  };

  return (
    <div
      className={`rounded-[6px] border border-border bg-surface p-4 text-text ${className}`}
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 md:gap-2">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;

          return (
            <React.Fragment key={step.id}>
              {/* Step item */}
              <button
                type="button"
                onClick={() => handleStepClick(step)}
                className="flex items-center gap-2.5 text-left group hover:opacity-85 transition-opacity cursor-pointer shrink-0"
              >
                {renderStepIndicator(step)}
                <div className="min-w-0">
                  <div className="text-[13px] font-medium text-text group-hover:text-accent transition-colors leading-tight">
                    {step.title}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-text-3">
                      {step.statusText}
                    </span>
                    {step.timestamp && (
                      <span className="text-[10px] font-mono text-text-3">
                        {step.timestamp}
                      </span>
                    )}
                  </div>
                </div>
              </button>

              {/* 1px connecting hairline */}
              {!isLast && (
                <div className="hidden md:block flex-1 h-[1px] bg-border mx-2" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
