"""Execute fixed educational programs only; no user/model code is evaluated."""
import copy
import re
import sqlite3
from backend.services.director import sentences

KINDS = {'python_variables','python_condition','python_loop','sql_filter','sql_join'}
DEFAULT_VALUES = [12,25,8]


def validate_spec(spec,narration):
    if spec == {'kind':'off'}:
        return
    if not isinstance(spec,dict) or set(spec)!={'kind','values','threshold','sentence'} or spec['kind'] not in KINDS:
        raise ValueError('Choose a supported Python or SQL demonstration')
    if not isinstance(spec['values'],list) or not 2<=len(spec['values'])<=5 or any(type(v) is not int or not -100<=v<=100 for v in spec['values']):
        raise ValueError('Use two to five integer example values between -100 and 100')
    if type(spec['threshold']) is not int or not -100<=spec['threshold']<=100:
        raise ValueError('Example threshold must be an integer between -100 and 100')
    if type(spec['sentence']) is not int or not 0<=spec['sentence']<len(sentences(narration)):
        raise ValueError('Example timing must reference a narration sentence')


def select_spec(scene):
    authored=scene.get('visual',{}).get('demo')
    if authored is not None:
        validate_spec(authored,scene['narration'])
        return None if authored['kind']=='off' else copy.deepcopy(authored)
    if scene.get('visual',{}).get('worked') or scene.get('visual',{}).get('codeLines'):
        return None
    text=scene['narration']
    # Preserve authored numeric examples rather than inventing matching inputs.
    if re.search(r'\d',text):return None
    if re.search(r'[<>=]|\bprint\s*\(',text):return None
    kind=None
    context=scene.get('topic','')+' '+scene.get('headline','')+' '+text
    if re.search(r'\bpython\b',context,re.I) and not re.search(r'\bSQL\b',text,re.I):
        if re.search(r'\b(for loop|loops?|iterate|iteration)\b',text,re.I):kind='python_loop'
        elif re.search(r'\b(if|condition|conditional|branch)\b',text,re.I):kind='python_condition'
        elif re.search(r'\bvariables?|assignment\b',text,re.I):kind='python_variables'
    elif re.search(r'\bSQL\b',context,re.I):
        if re.search(r'\b(?:inner join|joins?)\b',text,re.I) and not re.search(r'\b(left|right|outer|cross)\s+join',text,re.I):kind='sql_join'
        elif re.search(r'\b(where|filter\w*)\b',text,re.I):kind='sql_filter'
    if not kind:return None
    if kind in {'python_condition','sql_filter'} and re.search(r'\b(?:less than|below|under|equal to|greater than|not equal)\b',text,re.I):return None
    pattern={'python_loop':r'loop|iterat','python_condition':r'condition|\bif\b|branch','python_variables':r'variable|assign','sql_filter':r'where|filter','sql_join':r'join'}[kind]
    cue=next(i for i,p in enumerate(sentences(text)) if re.search(pattern,p,re.I))
    return {'kind':kind,'values':DEFAULT_VALUES[:],'threshold':15,'sentence':cue}


def compute(spec):
    """Inputs are bounded integers; programs and SQL statements are internal constants."""
    validate_spec(spec,'Example sentence. '* (spec.get('sentence',0)+1))
    if spec['kind']=='off':raise ValueError('Disabled example')
    values=spec['values'];kind=spec['kind'];threshold=spec['threshold']
    result={'spec':copy.deepcopy(spec),'provenance':'computed_example','steps':[]}
    if kind.startswith('python_'):
        output=[]
        def checkpoint(line,scope):
            variables={k:v for k,v in scope.items() if k in {'count','score','passed','total','amount'}}
            result['steps'].append({'line':line,'variables':variables,'output':output[:]})
        if kind=='python_variables':
            lines=[f'count = {values[0]}',f'count = count + {values[1]}','print(count)']
            program='\n'.join(f'{line}\ncheckpoint({i}, locals())' for i,line in enumerate(lines,1))
        elif kind=='python_condition':
            lines=[f'score = {values[0]}',f'if score >= {threshold}:','    passed = True','else:','    passed = False','print(passed)']
            program=f'{lines[0]}\ncheckpoint(1, locals())\ncheckpoint(2, locals())\n{lines[1]}\n{lines[2]}\n    checkpoint(3, locals())\nelse:\n{lines[4]}\n    checkpoint(5, locals())\nprint(passed)\ncheckpoint(6, locals())'
        else:
            lines=['total = 0',f'for amount in {values}:','    total += amount','print(total)']
            program=f'total = 0\ncheckpoint(1, locals())\n{lines[1]}\n    checkpoint(2, locals())\n    total += amount\n    checkpoint(3, locals())\nprint(total)\ncheckpoint(4, locals())'
        # Only our fixed templates reach compile/exec. No free-form snippets,
        # imports, filesystem, network, or model-provided expressions are accepted.
        scope={'__builtins__':{'locals':locals,'print':lambda value:output.append(str(value))},'checkpoint':checkpoint}
        exec(compile(program,'<visualforge-fixed-example>','exec'),scope)
        result.update(code=lines,output=output,engine='CPython fixed template')
    else:
        customers=[[1,'Alice'],[2,'Bob'],[3,'Cara']]
        orders=[[i+1,[1,2,1,3,2][i],value] for i,value in enumerate(values)]
        with sqlite3.connect(':memory:') as connection:
            connection.executescript('CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER);')
            connection.executemany('INSERT INTO customers VALUES (?,?)',customers)
            connection.executemany('INSERT INTO orders VALUES (?,?,?)',orders)
            if kind=='sql_filter':
                sql='SELECT id, amount FROM orders WHERE amount >= ? ORDER BY id'
                rows=[list(row) for row in connection.execute(sql,(threshold,))]
                code=['SELECT id, amount','FROM orders',f'WHERE amount >= {threshold}','ORDER BY id;'];columns=['id','amount']
            else:
                sql='SELECT orders.id, customers.name, orders.amount FROM orders INNER JOIN customers ON orders.customer_id = customers.id ORDER BY orders.id'
                rows=[list(row) for row in connection.execute(sql)]
                code=['SELECT orders.id, customers.name, orders.amount','FROM orders INNER JOIN customers','ON orders.customer_id = customers.id','ORDER BY orders.id;'];columns=['id','name','amount']
        accumulated=[]
        for order in orders:
            matching=[row for row in rows if row[0]==order[0]]
            accumulated.extend(matching)
            result['steps'].append({'line':3,'order_id':order[0],'customer_id':order[1] if kind=='sql_join' else None,'rows':copy.deepcopy(accumulated),'matched':bool(matching)})
        result.update(code=code,orders=orders,customers=customers,columns=columns,rows=rows,engine='SQLite in-memory SELECT')
    return result


def narration_issues(scene):
    spec=select_spec(scene)
    if not spec:return []
    data=compute(spec);text=scene['narration'];issues=[]
    claim=re.search(r'\b(?:prints?|output is|result is)\s+(-?\d+)\b',text,re.I) if spec['kind'].startswith('python_') else re.search(r'\breturns?\s+(\d+)\s+rows?\b',text,re.I)
    if claim:
        actual=data['output'][-1] if spec['kind'].startswith('python_') else str(len(data['rows']))
        if claim[1]!=actual:issues.append({'code':'example_output_mismatch','severity':'error','message':f'The computed example returns {actual}, but the narration states {claim[1]}. Change the example inputs or narration.'})
    return issues


def timed_example(scene,beats):
    spec=select_spec(scene)
    if not spec:return None
    result=compute(spec)
    cue=spec['sentence']
    if cue>=len(beats):raise ValueError('Example needs measured sentence timing')
    start=beats[cue]['start'];end=beats[-1]['end']
    result['at']=[start+i*max(0,end-start-.3)/max(1,len(result['steps'])-1) for i in range(len(result['steps']))]
    return result
