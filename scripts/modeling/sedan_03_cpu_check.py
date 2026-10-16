"""Exercise Study authoring calls without Blender; this is not a render review."""
import ast
import json
import math
import runpy
import sys
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


class Node(dict):
    __hash__=object.__hash__

    def __init__(self,name,origin=(0,0,0),parent=None):
        super().__init__(origin_carvue=list(origin))
        self.name=name
        self.parent=parent
        self.data=types.SimpleNamespace(set_sharp_from_angle=lambda **kwargs:None)


class Recorder:
    def __init__(self,vehicle_id,reference):
        self.root=Node('VehicleRoot')
        self.samples=0
        self.objects=0
        self.bounds={}
        self.manifest=None
        self.tyre_meshes={}
        self.tyre_gaps=[]

    def group(self,name,origin=(0,0,0),parent=None):
        return Node(name,origin,parent)

    def material(self,name,*args,**kwargs):
        return name

    def mesh(self,name,vertices,faces,mat,parent=None,smooth=True,normal=None):
        assert vertices and faces, name+' is empty'
        assert all(len(face)>=3 and all(0<=index<len(vertices) for index in face) for face in faces),name
        self.record(name,vertices)
        return Node(name)

    def record(self,name,vertices):
        assert all(len(p)==3 and all(math.isfinite(float(n)) for n in p) for p in vertices),name+' has nonfinite vertices'
        self.samples+=len(vertices)
        self.objects+=1
        low=[min(p[i] for p in vertices) for i in range(3)]
        high=[max(p[i] for p in vertices) for i in range(3)]
        old=self.bounds.get(name)
        if old:
            low=[min(low[i],old['min'][i]) for i in range(3)]
            high=[max(high[i],old['max'][i]) for i in range(3)]
        self.bounds[name]={'min':low,'max':high}

    def surface(self,name,fn,nu,nv,mat,parent=None,solid=0,normal=None):
        vertices=[fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)]
        self.record(name,vertices)
        if name.startswith('Tyre'):
            self.tyre_meshes[parent]=(vertices,nu,nv)
        if name in ['TreadChannel','TreadSipe']:
            tyre,around,across=self.tyre_meshes[parent]
            cx,cy,cz=parent['origin_carvue']
            width=.225 if cz>0 else .245
            for x,y,z in vertices:
                angle=math.atan2(z-cz,y-cy)%math.tau
                column=min(around-1,int(angle/math.tau*around))
                fraction=max(0,min(across,((x-cx)/width+.5)*across))
                row=min(across-1,int(fraction))
                blend=fraction-row
                segment=[]
                for col in [column,column+1]:
                    p,q=tyre[row*(around+1)+col],tyre[(row+1)*(around+1)+col]
                    segment.append((p[1]+(q[1]-p[1])*blend-cy,p[2]+(q[2]-p[2])*blend-cz))
                p,q=segment
                dy,dz=q[0]-p[0],q[1]-p[1]
                intersect=(p[0]*dz-p[1]*dy)/(math.cos(angle)*dz-math.sin(angle)*dy)
                gap=math.hypot(y-cy,z-cz)-intersect
                assert -.00001<=gap<=.00010,(name,gap)
                self.tyre_gaps.append(gap)
        return Node(name)

    def thickness(self,obj,*args):
        return obj

    def box(self,name,centre,size,mat,parent=None,radius=.012):
        assert all(value>0 for value in size),name
        self.record(name,[tuple(centre[i]+sign*size[i]*.5 for i in range(3)) for sign in [-1,1]])
        return Node(name)

    def curve(self,name,points,radius,mat,parent=None,cyclic=False,bezier=False):
        assert len(points)>=2,name+' curve has fewer than two points'
        self.record(name,points)
        return Node(name)

    def export(self,manifest,report):
        self.manifest=manifest
        assert manifest['vehicleId']=='sedan-03'
        assert len(manifest['joints'])==5
        result={'check':'CPU authoring-call and finite sample validation; not Blender geometry or visual approval',
                'status':'passed','sampledVertices':self.samples,'unmergedPrimitiveCalls':self.objects,
                'limitations':['No modifiers, normal calculation, material rendering, GLB export or visual review executed.'],
                'manifest':manifest,'selectedBounds':{key:value for key,value in self.bounds.items()
                    if key in ['Hood','RoofSkin','FrontBumperSkin','TrunkDeck','MovingTrunkFascia','CargoSideWall','CargoFloor']}}
        result['tyreSurfaceConformance']={'check':'Intersect authored tread vertices with the actual sampled tyre cross-section polygons.',
                                         'samples':len(self.tyre_gaps),'minimumRadialGapMm':min(self.tyre_gaps)*1000,
                                         'maximumRadialGapMm':max(self.tyre_gaps)*1000}
        output=ROOT/'assets/source/sedan-03/cpu-check.json'
        output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({key:result[key] for key in ['status','sampledVertices','unmergedPrimitiveCalls']},indent=2))


for path in [Path(__file__).parent/'build_sedan_03.py',*Path(__file__).parent.glob('sedan_03_*.py')]:
    ast.parse(path.read_text(encoding='utf-8'))
stub=types.ModuleType('vehicle_authoring')
stub.VehicleAuthoring=Recorder
sys.modules['vehicle_authoring']=stub
runpy.run_path(str(Path(__file__).parent/'build_sedan_03.py'),run_name='__main__')
