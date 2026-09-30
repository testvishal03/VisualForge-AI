import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {animationTiming} from '../animation';
import type {Scene} from '../types';

export function NeuralNetDiagram({scene, accent, panel}: {scene: Scene; accent: string; panel: string}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = scene.visual?.items ?? [];
  const labels = items.length > 0 ? items.slice(0, 4) : ['Input', 'Hidden', 'Hidden', 'Output'];
  const numLayers = Math.min(labels.length, 4);
  const nodesPerLayer = numLayers === 3 ? [4, 6, 3] : [4, 6, 6, 3];
  const layerX = Array.from({length: numLayers}).map((_, i) => 200 + i * (1200 / Math.max(1, numLayers - 1)));
  const yCenter = 175;
  const spacing = 44;
  const radius = 18;
  
  const currentT = frame / fps;
  const revealTimes = animationTiming(scene);
  
  const layerReveals = revealTimes.map(t => {
    return spring({frame: Math.max(0, frame - t * fps), fps, config: {damping: 14, stiffness: 120}});
  });
  const layerActive = revealTimes.map((t, i) => {
    const nextT = i < revealTimes.length - 1 ? revealTimes[i+1] : scene.duration;
    return currentT >= t && currentT < nextT;
  });

  const connections: React.ReactNode[] = [];
  const paths: {x1:number, y1:number, x2:number, y2:number, length:number, offset:number}[] = [];
  for (let l = 0; l < numLayers - 1; l++) {
    const nodesA = nodesPerLayer[l];
    const nodesB = nodesPerLayer[l+1];
    const x1 = layerX[l];
    const x2 = layerX[l+1];
    
    for (let i = 0; i < nodesA; i++) {
      const y1 = yCenter + (i - (nodesA - 1) / 2) * spacing;
      for (let j = 0; j < nodesB; j++) {
        const y2 = yCenter + (j - (nodesB - 1) / 2) * spacing;
        const active = layerActive[l];
        connections.push(
          <line key={`${l}-${i}-${j}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke={accent} strokeWidth="1.5" strokeOpacity={active ? 1 : 0.14} />
        );
        paths.push({x1, y1, x2, y2, length: Math.hypot(x2-x1, y2-y1), offset: (l * 100 + i * 30 + j * 70)});
      }
    }
  }

  const numPulses = 6;
  const pulses: React.ReactNode[] = [];
  for (let i=0; i<numPulses; i++) {
    if (paths.length === 0) break;
    const visiblePaths=paths.filter(p=>layerActive[layerX.indexOf(p.x1)]);
    if(!visiblePaths.length)break;
    const path = visiblePaths[i % visiblePaths.length];
    const progress = ((frame + path.offset + i * 40) % 150) / 150; 
    if (progress >= 0 && progress <= 1) {
      const px = interpolate(progress, [0, 1], [path.x1, path.x2]);
      const py = interpolate(progress, [0, 1], [path.y1, path.y2]);
      pulses.push(<circle key={`pulse-${i}`} cx={px} cy={py} r={6} fill={accent} opacity={0.8} />);
    }
  }

  const nodes: React.ReactNode[] = [];
  for (let l = 0; l < numLayers; l++) {
    const nodesA = nodesPerLayer[l];
    const x1 = layerX[l];
    const r = layerReveals[l];
    const scale = interpolate(r, [0, 1], [0.6, 1.0]);
    const active = layerActive[l];
    
    for (let i = 0; i < nodesA; i++) {
      const y1 = yCenter + (i - (nodesA - 1) / 2) * spacing;
      nodes.push(
        <circle key={`node-${l}-${i}`} cx={x1} cy={y1} r={radius * scale} fill={panel} stroke={active ? accent : `${accent}55`} strokeWidth="3" opacity={r} style={{filter: active ? `drop-shadow(0 0 8px ${accent})` : 'none'}}/>
      );
    }
    
    nodes.push(
      <foreignObject key={`label-${l}`} x={x1-150} y={325} width={300} height={65} opacity={r}><div style={{color:accent,fontSize:22,textAlign:'center',lineHeight:1.2}}>{labels[l]}</div></foreignObject>
    );
  }

  return (
    <div style={{height: 420, position: 'relative'}}>
      <svg viewBox="0 0 1600 420" style={{width: '100%', height: '100%'}}>
        {connections}
        {pulses}
        {nodes}
        <text x="800" y="410" textAnchor="middle" fill={accent} fontSize="17">Schematic connections - not measured activations</text>
      </svg>
    </div>
  );
}
