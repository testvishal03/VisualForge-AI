import type {Scene} from './types.ts';
export type DemoSpec={kind:'python_variables'|'python_condition'|'python_loop'|'sql_filter'|'sql_join';values:number[];threshold:number;sentence:number};
export type DemoStep={line:number;variables?:Record<string,number|boolean>;output?:string[];order_id?:number;customer_id?:number|null;rows?:(number|string)[][];matched?:boolean};
export type CodeExample={spec:DemoSpec;provenance:'computed_example';engine:string;code:string[];steps:DemoStep[];at:number[];output?:string[];orders?:number[][];customers?:(number|string)[][];columns?:string[];rows?:(number|string)[][]};

const same=(a:unknown,b:unknown):boolean=>{
  const canonical=(v:unknown):unknown=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort().map(([k,x])=>[k,canonical(x)])):v;
  return JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
};

export function validateCodeExample(scene:Scene){
  const demo=scene.demonstration;if(!demo)return;
  const fail=()=>{throw new Error('Invalid computed Python/SQL example.');};
  const spec=demo.spec;
  if(!spec||!['python_variables','python_condition','python_loop','sql_filter','sql_join'].includes(spec.kind)||!Array.isArray(spec.values)||spec.values.length<2||spec.values.length>5||spec.values.some(v=>!Number.isInteger(v)||Math.abs(v)>100)||!Number.isInteger(spec.threshold)||Math.abs(spec.threshold)>100||!Number.isInteger(spec.sentence)||!scene.beats?.[spec.sentence]||demo.provenance!=='computed_example')fail();
  const [a,b]=spec.values;const expected:DemoStep[]=[];
  const expectedCode=spec.kind==='python_variables'?[`count = ${a}`,`count = count + ${b}`,'print(count)']:
    spec.kind==='python_condition'?[`score = ${a}`,`if score >= ${spec.threshold}:`,'    passed = True','else:','    passed = False','print(passed)']:
    spec.kind==='python_loop'?['total = 0',`for amount in [${spec.values.join(', ')}]:`,'    total += amount','print(total)']:
    spec.kind==='sql_filter'?['SELECT id, amount','FROM orders',`WHERE amount >= ${spec.threshold}`,'ORDER BY id;']:
    ['SELECT orders.id, customers.name, orders.amount','FROM orders INNER JOIN customers','ON orders.customer_id = customers.id','ORDER BY orders.id;'];
  if(!same(demo.code,expectedCode))fail();
  if(spec.kind==='python_variables'){
    expected.push({line:1,variables:{count:a},output:[]},{line:2,variables:{count:a+b},output:[]},{line:3,variables:{count:a+b},output:[String(a+b)]});
  }else if(spec.kind==='python_condition'){
    const passed=a>=spec.threshold;
    expected.push({line:1,variables:{score:a},output:[]},{line:2,variables:{score:a},output:[]},{line:passed?3:5,variables:{score:a,passed},output:[]},{line:6,variables:{score:a,passed},output:[passed?'True':'False']});
  }else if(spec.kind==='python_loop'){
    let total=0;expected.push({line:1,variables:{total},output:[]});
    for(const amount of spec.values){expected.push({line:2,variables:{total,amount},output:[]});total+=amount;expected.push({line:3,variables:{total,amount},output:[]});}
    expected.push({line:4,variables:{total,amount:spec.values.at(-1)!},output:[String(total)]});
  }else{
    const customers=[[1,'Alice'],[2,'Bob'],[3,'Cara']],orders=spec.values.map((amount,i)=>[i+1,[1,2,1,3,2][i],amount]);
    if(!same(demo.customers,customers)||!same(demo.orders,orders))fail();
    const rows:(number|string)[][]=[];
    for(const order of orders){const matched=spec.kind==='sql_join'||order[2]>=spec.threshold;
      if(matched)rows.push(spec.kind==='sql_join'?[order[0],customers[order[1]-1][1],order[2]]:[order[0],order[2]]);
      expected.push({line:3,order_id:order[0],customer_id:spec.kind==='sql_join'?order[1]:null,rows:rows.map(r=>[...r]),matched});
    }
    if(!same(demo.rows,rows)||!same(demo.columns,spec.kind==='sql_join'?['id','name','amount']:['id','amount']))fail();
  }
  if(!same(demo.steps,expected)||!Array.isArray(demo.code)||!demo.code.length||demo.code.some(line=>typeof line!=='string'||line.length>150)||!Array.isArray(demo.at)||demo.at.length!==expected.length||demo.at.some((at,i)=>!Number.isFinite(at)||at<scene.beats![spec.sentence].start||at>scene.duration||(i>0&&at<demo.at[i-1])))fail();
  if(spec.kind.startsWith('python_')&&!same(demo.output,expected.at(-1)!.output))fail();
}

export function demonstrationStep(demo:CodeExample,time:number){return demo.at.reduce((active,at,i)=>time>=at?i:active,0);}
