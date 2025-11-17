import React, { useEffect, useState, useRef } from 'react';

interface Position {
  x: number;
  y: number;
}

interface DataFlowAnimationProps {
  fromNode: { position: Position; id: string } | undefined;
  toNode: { position: Position; id: string } | undefined;
  onComplete?: () => void;
}

export const DataFlowAnimation: React.FC<DataFlowAnimationProps> = ({
  fromNode,
  toNode,
  onComplete
}) => {
  const [position, setPosition] = useState<Position>({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(1);
  const animationFrameRef = useRef<number>();

  useEffect(() => {
    if (!fromNode || !toNode) {
      return;
    }

    // Calculate start and end positions (center of nodes)
    const startX = fromNode.position.x + 100; // Assuming 200px wide nodes
    const startY = fromNode.position.y + 40;  // Assuming 80px tall nodes
    const endX = toNode.position.x + 100;
    const endY = toNode.position.y + 40;

    const startTime = Date.now();
    const duration = 1000; // 1 second

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function for smooth animation
      const easeProgress = 1 - Math.pow(1 - progress, 3);

      setPosition({
        x: startX + (endX - startX) * easeProgress,
        y: startY + (endY - startY) * easeProgress
      });

      // Fade out near the end
      if (progress > 0.8) {
        setOpacity(1 - (progress - 0.8) * 5);
      }

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        onComplete?.();
      }
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [fromNode, toNode, onComplete]);

  if (!fromNode || !toNode) {
    return null;
  }

  return (
    <div
      className="data-flow-particle absolute pointer-events-none"
      style={{
        left: position.x - 6,
        top: position.y - 6,
        width: 12,
        height: 12,
        borderRadius: '50%',
        backgroundColor: '#4CAF50',
        boxShadow: `0 0 ${10 * opacity}px rgba(76, 175, 80, ${opacity})`,
        opacity: opacity,
        zIndex: 1000,
        transition: 'none'
      }}
    />
  );
};

interface DataFlowContainerProps {
  flows: Array<{
    id: string;
    fromNode: { position: Position; id: string } | undefined;
    toNode: { position: Position; id: string } | undefined;
  }>;
  onFlowComplete: (id: string) => void;
}

export const DataFlowContainer: React.FC<DataFlowContainerProps> = ({
  flows,
  onFlowComplete
}) => {
  return (
    <>
      {flows.map((flow) => (
        <DataFlowAnimation
          key={flow.id}
          fromNode={flow.fromNode}
          toNode={flow.toNode}
          onComplete={() => onFlowComplete(flow.id)}
        />
      ))}
    </>
  );
};
