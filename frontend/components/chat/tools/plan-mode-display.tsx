'use client';

import type { ChatMessage } from '@/types';
import { cn } from '@/lib/utils';
import { ClipboardList, CheckCircle, AlertCircle } from 'lucide-react';
import { NonCollapsibleToolCard } from './tool-card';
import { RunningIndicator } from './tool-status-badge';

interface PlanModeDisplayProps {
  message: ChatMessage;
  isRunning: boolean;
}

/**
 * Display for EnterPlanMode - shows that Claude is entering planning mode
 */
export function EnterPlanModeDisplay({ message, isRunning }: PlanModeDisplayProps) {
  return (
    <NonCollapsibleToolCard
      toolName="Entering Plan Mode"
      ToolIcon={ClipboardList}
      color="hsl(var(--tool-plan))"
      isRunning={isRunning}
      timestamp={message.timestamp}
      ariaLabel={`Entering plan mode${isRunning ? ', analyzing task' : ''}`}
      headerContent={
        <>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded border"
            style={{
              backgroundColor: 'hsl(var(--tool-plan) / 0.1)',
              color: 'hsl(var(--tool-plan))',
              borderColor: 'hsl(var(--tool-plan) / 0.2)',
            }}
            aria-hidden="true"
          >
            Planning
          </span>
          {isRunning && (
            <span className="ml-auto">
              <RunningIndicator label="Analyzing" color="hsl(var(--tool-plan))" />
            </span>
          )}
        </>
      }
    >
      <div className="px-3 py-2">
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Claude is analyzing the task and will propose an implementation plan for your approval.
        </p>
      </div>
    </NonCollapsibleToolCard>
  );
}

/**
 * Display for ExitPlanMode - shows the plan ready for approval
 */
export function ExitPlanModeDisplay({ message, isRunning }: PlanModeDisplayProps) {
  const input = message.toolInput || {};
  const launchSwarm = input.launchSwarm as boolean | undefined;
  const teammateCount = input.teammateCount as number | undefined;
  const allowedPrompts = input.allowedPrompts as
    | Array<{ tool: string; prompt: string }>
    | undefined;
  const pushToRemote = input.pushToRemote as boolean | undefined;
  const remoteSessionTitle = input.remoteSessionTitle as string | undefined;

  const permissionCount = allowedPrompts?.length || 0;
  const hasDetails = launchSwarm || permissionCount > 0 || pushToRemote;

  return (
    <NonCollapsibleToolCard
      toolName="ExitPlanMode"
      ToolIcon={CheckCircle}
      color="hsl(var(--tool-plan))"
      isRunning={isRunning}
      timestamp={message.timestamp}
      ariaLabel={`Plan mode completed${launchSwarm ? `, using ${teammateCount || 'auto'} agents` : ''}${permissionCount > 0 ? `, ${permissionCount} permissions requested` : ''}`}
      headerContent={
        <>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded border"
            style={{
              backgroundColor: 'hsl(var(--progress-high) / 0.1)',
              color: 'hsl(var(--progress-high))',
              borderColor: 'hsl(var(--progress-high) / 0.2)',
            }}
            aria-hidden="true"
          >
            Plan Complete
          </span>
          {isRunning && (
            <span className="ml-auto">
              <RunningIndicator label="Processing" color="hsl(var(--tool-plan))" />
            </span>
          )}
        </>
      }
    >
      <div className="p-3 space-y-2">
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Planning phase has concluded. {hasDetails ? 'Implementation details:' : 'Ready to proceed with implementation.'}
        </p>
        {/* Execution details */}
        {hasDetails && (
          <PlanExecutionDetails
            launchSwarm={launchSwarm}
            teammateCount={teammateCount}
            pushToRemote={pushToRemote}
            remoteSessionTitle={remoteSessionTitle}
            permissionCount={permissionCount}
          />
        )}
        {/* Permissions list */}
        {allowedPrompts && allowedPrompts.length > 0 && (
          <PermissionsList permissions={allowedPrompts} />
        )}
      </div>
    </NonCollapsibleToolCard>
  );
}

interface PlanExecutionDetailsProps {
  launchSwarm?: boolean;
  teammateCount?: number;
  pushToRemote?: boolean;
  remoteSessionTitle?: string;
  permissionCount: number;
}

/**
 * Displays execution detail badges for plan mode
 */
function PlanExecutionDetails({
  launchSwarm,
  teammateCount,
  pushToRemote,
  remoteSessionTitle,
  permissionCount,
}: PlanExecutionDetailsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {launchSwarm && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-status-info-bg text-status-info border border-status-info/20">
          Swarm: {teammateCount || 'auto'} agents
        </span>
      )}
      {pushToRemote && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-500 border border-purple-500/20">
          Remote: {remoteSessionTitle || 'Claude.ai'}
        </span>
      )}
      {permissionCount > 0 && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-status-warning-bg text-status-warning-fg border border-status-warning/20">
          {permissionCount} permission{permissionCount > 1 ? 's' : ''} requested
        </span>
      )}
    </div>
  );
}

interface PermissionsListProps {
  permissions: Array<{ tool: string; prompt: string }>;
}

/**
 * Lists requested permissions in plan mode
 */
function PermissionsList({ permissions }: PermissionsListProps) {
  return (
    <div className="space-y-1 pt-1">
      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
        Requested Permissions
      </span>
      <div className="space-y-1">
        {permissions.map((perm, idx) => (
          <div
            key={idx}
            className="flex items-center gap-2 text-[11px] text-muted-foreground"
          >
            <AlertCircle className="h-3 w-3 text-status-warning" />
            <span className="font-mono text-[10px] bg-muted/50 px-1 rounded">
              {perm.tool}
            </span>
            <span>{perm.prompt}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
