/** Geometry and styling rules for items travelling along connections. */
export type Point=[number,number];

/** Point on a quadratic Bézier, the same curve the connection arrows draw. */
export function along(from:Point,control:Point,to:Point,u:number):Point{
  const a=(1-u)*(1-u),b=2*(1-u)*u,c=u*u;
  return [a*from[0]+b*control[0]+c*to[0],a*from[1]+b*control[1]+c*to[1]];
}

/** What travels along a connection, chosen from the object it arrives at. */
export function chipKind(label:string){
  const value=label.toLowerCase();
  if(/token|\bwords?\b|\bpieces?\b|\btext\b|\bids?\b/.test(value))return 'chip';
  if(/document|evidence|source|page|policy|file/.test(value))return 'page';
  return 'dot';
}
