# File created by Diego Thomas the 21-11-2016
# Second Author Inoe AMDRE

# File to handle program main loop
import sys
import cv2
from math import cos,sin
import numpy as np
from numpy import linalg as LA
from numpy.matlib import rand,zeros,ones,empty,eye
import Tkinter as tk
import tkMessageBox
from tkFileDialog import askdirectory
from PIL import Image, ImageTk
import imp
import scipy.io
import time
import pyopencl as cl




RGBD = imp.load_source('RGBD', './lib/RGBD.py')
RGBDimg = imp.load_source('RGBDimg', './lib/RGBDimg.py')
TrackManager = imp.load_source('TrackManager', './lib/tracking.py')
TSDFtk = imp.load_source('TSDFtk', './lib/TSDF.py')
GPU = imp.load_source('GPUManager', './lib/GPUManager.py')
My_MC = imp.load_source('My_MarchingCube', './lib/My_MarchingCube.py')
Stitcher = imp.load_source('Stitcher', './lib/Stitching.py')

def in_mat_zero2one(mat):
    """This fonction replace in the matrix all the 0 to 1"""
    mat_tmp = (mat != 0.0)
    res = mat * mat_tmp + ~mat_tmp
    return res

class Application(tk.Frame):
    ## Function to handle keyboard inputs
    def key(self, event):
        Transfo = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        
        if (event.keysym == 'Escape'):
            self.root.destroy()
        if (event.keysym == 'd'):
            Transfo[0,3] = -0.1
        if (event.keysym == 'a'):
            Transfo[0,3] = 0.1
        if (event.keysym == 'w'):
            Transfo[1,3] = 0.1
        if (event.keysym == 's'):
            Transfo[1,3] = -0.1
        if (event.keysym == 'e'):
            Transfo[2,3] = 0.1
        if (event.keysym == 'q'):
            Transfo[2,3] = -0.1
        if (event.keysym == 'c'):
            self.color_tag = (self.color_tag+1) %2

        if (event.keysym != 'Escape'):
            self.Pose = np.dot(self.Pose, Transfo)
            rendering =np.zeros((self.Size[0], self.Size[1], 3), dtype = np.uint8)
            rendering = self.RGBD2.Draw_optimize(rendering,self.Pose, self.w.get(), self.color_tag)
            rendering = self.RGBD.DrawMesh(rendering, self.MC.Vertices,self.MC.Normals,self.Pose, 1, self.color_tag)
            img = Image.fromarray(rendering, 'RGB')
            self.imgTk=ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgTk)
            #self.DrawCenters2D(self.Pose)
            #self.DrawSys2D(self.Pose)
            #self.DrawOBBox2D(self.Pose)


    ## Function to handle mouse press event
    def mouse_press(self, event):
        self.x_init = event.x
        self.y_init = event.y
    
    ## Function to handle mouse release events
    def mouse_release(self, event):
        x = event.x
        y = event.y
    
    
    ## Function to handle mouse motion events
    def mouse_motion(self, event):
        if (event.y < 480):
            delta_x = event.x - self.x_init
            delta_y = event.y - self.y_init
            
            angley = 0.
            if (delta_x > 0.):
                angley = -0.01
            elif (delta_x < 0.):
                angley = 0.01 #pi * 2. * delta_x / float(self.Size[0])
            RotY = np.array([[cos(angley), 0., sin(angley), 0.], \
                             [0., 1., 0., 0.], \
                             [-sin(angley), 0., cos(angley), 0.], \
                             [0., 0., 0., 1.]])
            self.Pose = np.dot(self.Pose, RotY)
            
            anglex = 0.
            if (delta_y > 0.):
                anglex = 0.01
            elif (delta_y < 0.):
                anglex = -0.01 # pi * 2. * delta_y / float(self.Size[0])
            RotX = np.array([[1., 0., 0., 0.], \
                            [0., cos(anglex), -sin(anglex), 0.], \
                            [0., sin(anglex), cos(anglex), 0.], \
                            [0., 0., 0., 1.]])

            self.Pose = np.dot(self.Pose, RotX)
            rendering =np.zeros((self.Size[0], self.Size[1], 3), dtype = np.uint8)
            rendering = self.RGBD2.Draw_optimize(rendering,self.Pose, self.w.get(), self.color_tag)
            rendering = self.RGBD.DrawMesh(rendering, self.MC.Vertices,self.MC.Normals,self.Pose, 1, self.color_tag)
            img = Image.fromarray(rendering, 'RGB')
            self.imgTk=ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgTk)
            #self.DrawCenters2D(self.Pose)
            #self.DrawSys2D(self.Pose)
            #self.DrawOBBox2D(self.Pose)
       
        self.x_init = event.x
        self.y_init = event.y

    def DrawPoint2D(self,point,radius,color):
        if point[0]>0 and point[1]>0:
            x1, y1 = (point[0] - radius), (point[1] - radius)
            x2, y2 = (point[0] + radius), (point[1] + radius)
        else:
            x1, y1 = (point[0]), (point[1])
            x2, y2 = (point[0]), (point[1]) 
        self.canvas.create_oval(x1, y1, x2, y2, fill=color)


    def DrawColors2D(self,RGBD,img,Pose):
        '''this function draw the color of each segmented part of the body'''
        newImg = img.copy()
        Txy = RGBD.transCrop
        label = RGBD.labels
        for k in range(1,RGBD.bdyPart.shape[0]+1):
            color = RGBD.bdyColor[k-1]
            for i in range(Txy[1],Txy[3]):
                for j in range(Txy[0],Txy[2]):
                    if label[i][j]==k :
                        newImg[i,j] = color
                    else :
                        newImg[i,j] = newImg[i,j] 
        return newImg               

                      
    def DrawSkeleton2D(self,Pose):
        '''this function draw the Skeleton of a human and make connections between each part'''
        pos = self.pos2d[0][self.Index]
        for i in range(np.size(self.connection,0)): 
            pt1 = (pos[self.connection[i,0]-1,0],pos[self.connection[i,0]-1,1])
            pt2 = (pos[self.connection[i,1]-1,0],pos[self.connection[i,1]-1,1])
            radius = 1
            color = "blue"        
            self.DrawPoint2D(pt1,radius,color)
            self.DrawPoint2D(pt2,radius,color)      
            self.canvas.create_line(pt1[0],pt1[1],pt2[0],pt2[1],fill="red")

    def DrawCenters2D(self,Pose,s=1):
        '''this function draw the center of each oriented coordinates system for each body part''' 
        self.ctr2D = self.RGBD.GetProjPts2D_optimize(self.RGBD.ctr3D,Pose)        
        for i in range(1, len(self.RGBD.ctr3D)):
            c = self.ctr2D[i]
            self.DrawPoint2D(c,2,"yellow")

    def DrawSys2D(self,Pose):
        '''this function draw the sys of oriented coordinates system for each body part''' 
        self.RGBD.GetNewSys(Pose,self.ctr2D,10)
        for i in range(1,len(self.ctr2D)):
            c = self.ctr2D[i]
            #print 'c'
            #print c
            pt0 = self.RGBD.drawNewSys[i-1][0]
            pt1 = self.RGBD.drawNewSys[i-1][1]
            pt2 = self.RGBD.drawNewSys[i-1][2]    
            self.canvas.create_line(pt0[0],pt0[1],c[0],c[1],fill="gray",width = 2)
            self.canvas.create_line(pt1[0],pt1[1],c[0],c[1],fill="gray",width = 2)
            self.canvas.create_line(pt2[0],pt2[1],c[0],c[1],fill="gray",width = 2)

    def DrawOBBox2D(self,Pose):
        '''Draw in the canvas the oriented bounding boxes for each body part''' 
        self.OBBcoords2D = []  
        self.OBBcoords2D.append([0.,0.,0.])
        # for each body part
        for i in range(1,len(self.RGBD.coordsGbl)):
            self.OBBcoords2D.append(self.RGBD.GetProjPts2D_optimize(self.RGBD.coordsGbl[i],Pose))
            pt = self.OBBcoords2D[i]
            #print 'self.OBBcoords2D[]'
            #print pt.shape
            # create lines of the boxes
            for j in range(3):
                self.canvas.create_line(pt[j][0],pt[j][1],pt[j+1][0],pt[j+1][1],fill="red",width =2)
                self.canvas.create_line(pt[j+4][0],pt[j+4][1],pt[j+5][0],pt[j+5][1],fill="red",width = 2)
                self.canvas.create_line(pt[j][0],pt[j][1],pt[j+4][0],pt[j+4][1],fill="red",width = 2)
            self.canvas.create_line(pt[3][0],pt[3][1],pt[0][0],pt[0][1],fill="red",width = 2)
            self.canvas.create_line(pt[7][0],pt[7][1],pt[4][0],pt[4][1],fill="red",width = 2)
            self.canvas.create_line(pt[3][0],pt[3][1],pt[7][0],pt[7][1],fill="red",width = 2)
            #draw points of the bounding boxes
            for j in range(8):
                self.DrawPoint2D(pt[j],2,"blue")
                
                
    def DrawOBBox2DLocal(self,Pose):
        '''Draw in the canvas the oriented bounding boxes for each body part''' 
        self.OBBcoords2DLcl = [] 
        self.OBBcoords2DLcl.append([0.,0.,0.])
        # for each body part
        for i in range(1,len(self.RGBD.coordsL)):
            self.OBBcoords2DLcl.append(self.RGBD.GetProjPts2D_optimize(self.RGBD.coordsL[i],Pose))
            pt = self.OBBcoords2DLcl[i]
            #print 'self.OBBcoords2D[]'
            #print pt
            # create lines of the boxes
            for j in range(3):
                self.canvas.create_line(pt[j][0],pt[j][1],pt[j+1][0],pt[j+1][1],fill="red",width =2)
                self.canvas.create_line(pt[j+4][0],pt[j+4][1],pt[j+5][0],pt[j+5][1],fill="red",width = 2)
                self.canvas.create_line(pt[j][0],pt[j][1],pt[j+4][0],pt[j+4][1],fill="red",width = 2)
            self.canvas.create_line(pt[3][0],pt[3][1],pt[0][0],pt[0][1],fill="red",width = 2)
            self.canvas.create_line(pt[7][0],pt[7][1],pt[4][0],pt[4][1],fill="red",width = 2)
            self.canvas.create_line(pt[3][0],pt[3][1],pt[7][0],pt[7][1],fill="red",width = 2)
            #draw points of the bounding boxes
            for j in range(8):
                self.DrawPoint2D(pt[j],2,"blue")                

    def DrawMesh2D(self,Pose,vertex,triangle):
        '''Draw in the canvas the triangles of the Mesh in 2D''' 
        python_green = "#476042"
        for i in range(triangle.shape[0]):
            pt0 = vertex[triangle[i][0]]
            pt1 = vertex[triangle[i][1]]
            pt2 = vertex[triangle[i][2]]
            self.canvas.create_polygon(pt0[0],pt0[1],pt1[0],pt1[1],pt2[0],pt2[1],outline = python_green, fill='yellow', width=1)


    def CheckVerts2D(self,verts):
        '''Change the indexes values that are outside the frame''' 
        #make sure there are not false values
        cdt_line = (verts[:,1] > -1) * (verts[:,1] < self.Size[0])
        cdt_column = (verts[:,0] > -1) * (verts[:,0] < self.Size[1])
        verts[:,0] = verts[:,0]*cdt_column
        verts[:,1] = verts[:,1]*cdt_line
        return verts     
       
    def InvPose(self,Pose):
        '''Compute the inverse transform of Pose''' 
        PoseInv = np.zeros(Pose.shape,Pose.dtype)
        PoseInv[0:3,0:3] = LA.inv(Pose[0:3,0:3])
        PoseInv[0:3,3] = -np.dot(PoseInv[0:3,0:3],Pose[0:3,3])
        PoseInv[3,3] = 1.0
        return PoseInv

    
    
    ## Constructor function
    def __init__(self, path,  GPUManager, master=None):
        self.root = master
        self.path = path
        self.GPUManager = GPUManager
        self.draw_bump = False
        self.draw_spline = False

        tk.Frame.__init__(self, master)
        self.pack()
        
        self.color_tag = 1
        calib_file = open(self.path + '/Calib.txt', 'r')
        calib_data = calib_file.readlines()
        self.Size = [int(calib_data[0]), int(calib_data[1])]
        self.intrinsic = np.array([[float(calib_data[2]), float(calib_data[3]), float(calib_data[4])], \
                                   [float(calib_data[5]), float(calib_data[6]), float(calib_data[7])], \
                                   [float(calib_data[8]), float(calib_data[9]), float(calib_data[10])]], dtype = np.float32)
    
        print self.intrinsic

        self.fact = 1000.0

        mat = scipy.io.loadmat(self.path + '/String4b.mat')
        self.lImages = mat['DepthImg']
        self.pos2d = mat['Pos2D']
        self.bdyIdx = mat['BodyIndex']


        connectionMat = scipy.io.loadmat(self.path + '/SkeletonConnectionMap.mat')
        self.connection = connectionMat['SkeletonConnectionMap']
        self.Pose = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]], dtype = np.float32)
        self.T_Pose = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]], dtype = np.float32)
        self.PoseBP = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]], dtype = np.float32)
        Id4 = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]], dtype = np.float32)
        
        # initialize lists because of  segmentation
        
        # Init for Local Transform and inverse Transform
        self.Tg = []
        self.Tg.append(Id4)
        # For Marching cubes output
        self.Vertices = []
        self.Vertices.append(np.zeros((1,3),np.float32))
        self.Normales = []
        self.Normales.append(np.zeros((1,3),np.float32))
        # Loop for each image
        i = 0

        # Former Depth Image (i.e: i)
        self.RGBD = RGBD.RGBD(self.path + '/Depth.tiff', self.path + '/RGB.tiff', self.intrinsic, self.fact)
        self.RGBD.LoadMat(self.lImages,self.pos2d,self.connection,self.bdyIdx )   
        self.Index = i
        self.RGBD.ReadFromMat(self.Index) 
        self.RGBD.BilateralFilter(-1, 0.02, 3) 
        # segmenting the body
        self.RGBD.Crop2Body() 
        self.RGBD.BodySegmentation() 
        self.RGBD.BodyLabelling()   
        # select the body part
        self.RGBD.depth_image *= (self.RGBD.labels >0) # 9 = head; 10 = torso 
        self.RGBD.Vmap_optimize()   
        self.RGBD.NMap_optimize()        
        # create the transform matrix from local to global coordinate
        self.RGBD.myPCA()

        '''
        The image is process differently from the other since it does not have any previous value.
        '''
        # Sum of the number of vertices and faces of all body parts
        nb_verticesGlo = 0
        nb_facesGlo = 0
        # Number of body part +1 since the counting starts from 1
        nbBdyPart = self.RGBD.bdyPart.shape[0]+1
        #Initiate stitcher object 
        self.StitchBdy = Stitcher.Stitch(nbBdyPart)        
        # Creating mesh of each body part
        for bp in range(1,nbBdyPart):
            # Compute the dimension of the body part to create the volume
            VoxSize = 0.0046
            X = int(round(LA.norm(self.RGBD.coordsGbl[bp][3]-self.RGBD.coordsGbl[bp][0])/VoxSize))
            Y = int(round(LA.norm(self.RGBD.coordsGbl[bp][1]-self.RGBD.coordsGbl[bp][0])/VoxSize))
            Z = X
            # show result
            print "X= %d; Y= %d; Z= %d" %(X,Y,Z)
            
            # Get the tranform matrix from the local coordinates system to the global system 
            Tglo = self.RGBD.TransfoBB[bp]
            self.Tg.append(Tglo.astype(np.float32))
            
            # Put the Global transfo in PoseBP so that the dtype entered in the GPU is correct
            for i in range(4):
                for j in range(4):
                    self.PoseBP[i][j] = self.Tg[bp][i][j]

            # TSDF  and Weight of the body part
            mf = cl.mem_flags
            self.TSDF = np.zeros((X,Y,Z), dtype = np.int16)
            self.TSDFGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.TSDF.nbytes)
            self.Weight = np.zeros((X,Y,Z), dtype = np.int16)
            self.WeightGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.Weight.nbytes)

            #rescaling factors
            param = np.array([X/2 , 1.0/VoxSize, Y/2 , 1.0/VoxSize, Z/2, 1.0/VoxSize], dtype = np.float32)

            # TSDF Fusion of the body part
            TSDFManager = TSDFtk.TSDFManager((X,Y,Z), self.RGBD, self.GPUManager,self.TSDFGPU,self.WeightGPU,param)
            TSDFManager.FuseRGBD_GPU(self.RGBD, self.PoseBP)

            # Create Mesh
            self.MC = My_MC.My_MarchingCube(TSDFManager.Size, TSDFManager.res, 0.0, self.GPUManager)     
            # Mesh rendering
            self.MC.runGPU(TSDFManager.TSDFGPU) 
#==============================================================================
#             start_time3 = time.time()
#             # save with the number of the body part
#             bpStr = str(bp)
#             self.MC.SaveToPly("body"+bpStr+".ply")
#             elapsed_time = time.time() - start_time3
#             print "SaveBPToPly: %f" % (elapsed_time)      
#==============================================================================
            
            #Fill list of MC's Vert and Nmls
            self.Vertices.append(self.MC.Vertices)
            self.Normales.append(self.MC.Normales)

            # Update number of vertices and faces in the stitched mesh
            nb_verticesGlo = nb_verticesGlo + self.MC.nb_vertices[0]
            nb_facesGlo = nb_facesGlo +self.MC.nb_faces[0]
            
            # Stitch all the body parts
            if bp ==1 :
                self.StitchBdy.StitchedVertices = self.StitchBdy.TransformVtx(self.MC.Vertices,self.PoseBP,1) 
                self.StitchBdy.StitchedNormales = self.StitchBdy.TransformNmls(self.MC.Normales,self.PoseBP,1) 
                self.StitchBdy.StitchedFaces = self.MC.Faces
            else:
                self.StitchBdy.NaiveStitch(self.MC.Vertices,self.MC.Normales,self.MC.Faces,self.PoseBP)
                    
#==============================================================================
#         # save with the number of the body part
#         start_time3 = time.time()
#         self.MC.SaveToPlyExt("wholeBody.ply",nb_verticesGlo,nb_facesGlo,self.StitchBdy.StitchedVertices,self.StitchBdy.StitchedFaces)
#         elapsed_time = time.time() - start_time3
#         print "SaveToPly: %f" % (elapsed_time)                      
#==============================================================================
        
        
        # Current Depth Image (i.e: i+1)
        self.newRGBD = RGBD.RGBD(self.path + '/Depth.tiff', self.path + '/RGB.tiff', self.intrinsic, self.fact)
        self.newRGBD.LoadMat(self.lImages,self.pos2d,self.connection,self.bdyIdx )   
        
        
        #TSDFManager = TSDFtk.TSDFManager((512,512,512), self.RGBD, self.GPUManager,self.TSDFGPU,self.WeightGPU,param2) 
        #self.MC = My_MC.My_MarchingCube(TSDFManager.Size, TSDFManager.res, 0.0, self.GPUManager)
        Tracker = TrackManager.Tracker(0.01, 0.5, 1, [10], 0.001)
        TimeStart = time.time()
        nbImg = 20
        for imgk in range(self.Index+1,nbImg):
            #Time counting
            start = time.time()
            '''
            Reinitialize every list
            '''
            # Init for Local Transform and inverse Transform
            self.Tg = []
            self.Tg.append(Id4)
            # For Marching cubes output
            self.Vertices = []
            self.Vertices.append(np.zeros((1,3),np.float32))
            self.Normales = []
            self.Normales.append(np.zeros((1,3),np.float32))  
            '''
            New Image 
            '''
            # Get new current image
            self.newRGBD.ReadFromMat(imgk) 
            self.newRGBD.BilateralFilter(-1, 0.02, 3) 
            # segmenting the body
            self.newRGBD.Crop2Body() 
            self.newRGBD.BodySegmentation() 
            self.newRGBD.BodyLabelling()   
            # select the body part
            self.newRGBD.depth_image *= (self.newRGBD.labels > 0) # 9 = head; 10 = torso 
            #self.newRGBD.depth_image *= (self.newRGBD.labels < 11) # 9 = head; 10 = torso 
            self.newRGBD.Vmap_optimize()   
            self.newRGBD.NMap_optimize()        
            # create the transform matrix from local to global coordinate
            self.newRGBD.myPCA()   
            
            
            # Transform the stitch body in the current image (alignment current image mesh) 
            # New pose estimation
            NewPose = Tracker.RegisterRGBDMesh_optimize(self.newRGBD,self.StitchBdy.StitchedVertices,self.StitchBdy.StitchedNormales, self.T_Pose)
            for k in range(4):
                for l in range(4):
                    self.T_Pose[k,l] = NewPose[k,l]
            print 'self.T_Pose'
            print self.T_Pose 

            
            # restart processing of each body part for the current image.
            # Sum of the number of vertices and faces of all body parts
            nb_verticesGlo = 0
            nb_facesGlo = 0
            #Initiate stitcher object 
            self.StitchBdy = Stitcher.Stitch(nbBdyPart)        
            # Creating mesh of each body part
            for bp in range(1,nbBdyPart):
                # Compute the dimension of the body part to create the volume
                VoxSize = 0.0046
                X = int(round(LA.norm(self.newRGBD.coordsGbl[bp][3]-self.newRGBD.coordsGbl[bp][0])/VoxSize))
                Y = int(round(LA.norm(self.newRGBD.coordsGbl[bp][1]-self.newRGBD.coordsGbl[bp][0])/VoxSize))
                Z = X
                # show result
                print "X= %d; Y= %d; Z= %d" %(X,Y,Z)
                
                # Get the tranform matrix from the local coordinates system to the global system 
                Tglo = self.newRGBD.TransfoBB[bp]
                self.Tg.append(Tglo.astype(np.float32))
                # Transform in the current image
                self.Tg[bp] = np.dot(self.Tg[bp],self.T_Pose)
                # Put the Global transfo in PoseBP so that the dtype entered in the GPU is correct
                for i in range(4):
                    for j in range(4):
                        self.PoseBP[i][j] = self.Tg[bp][i][j]
    
                # TSDF  and Weight of the body part
                mf = cl.mem_flags
                self.TSDF = np.zeros((X,Y,Z), dtype = np.int16)
                self.TSDFGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.TSDF.nbytes)
                self.Weight = np.zeros((X,Y,Z), dtype = np.int16)
                self.WeightGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.Weight.nbytes)
    
                #rescaling factors
                param = np.array([X/2 , 1.0/VoxSize, Y/2 , 1.0/VoxSize, Z/2, 1.0/VoxSize], dtype = np.float32)
    
                # TSDF Fusion of the body part
                TSDFManager = TSDFtk.TSDFManager((X,Y,Z), self.newRGBD, self.GPUManager,self.TSDFGPU,self.WeightGPU,param)
                TSDFManager.FuseRGBD_GPU(self.newRGBD, self.PoseBP)
    
                # Create Mesh
                self.MC = My_MC.My_MarchingCube(TSDFManager.Size, TSDFManager.res, 0.0, self.GPUManager)     
                # Mesh rendering
                self.MC.runGPU(TSDFManager.TSDFGPU) 
#==============================================================================
#                 start_time3 = time.time()
#                 # save with the number of the body part
#                 bpStr = str(bp)
#                 self.MC.SaveToPly("body"+bpStr+".ply")
#                 elapsed_time = time.time() - start_time3
#                 print "SaveBPToPly: %f" % (elapsed_time)      
#==============================================================================
                
                #Fill list of MC's Vert and Nmls
                self.Vertices.append(self.MC.Vertices)
                self.Normales.append(self.MC.Normales)
    
                # Update number of vertices and faces in the stitched mesh
                nb_verticesGlo = nb_verticesGlo + self.MC.nb_vertices[0]
                nb_facesGlo = nb_facesGlo +self.MC.nb_faces[0]
                
                # Stitch all the body parts
                if bp ==1 :
                    self.StitchBdy.StitchedVertices = self.StitchBdy.TransformVtx(self.MC.Vertices,self.PoseBP,1) 
                    self.StitchBdy.StitchedNormales = self.StitchBdy.TransformNmls(self.MC.Normales,self.PoseBP,1) 
                    self.StitchBdy.StitchedFaces = self.MC.Faces
                else:
                    self.StitchBdy.NaiveStitch(self.MC.Vertices,self.MC.Normales,self.MC.Faces,self.PoseBP)
            time_lapsed = time.time() - start
            print "numero %d finished : %f" %(imgk,time_lapsed)
                    

        # save with the number of the body part
        start_time3 = time.time()
        self.MC.SaveToPlyExt("wholeBody.ply",nb_verticesGlo,nb_facesGlo,self.StitchBdy.StitchedVertices,self.StitchBdy.StitchedFaces)
        elapsed_time = time.time() - start_time3
        print "SaveToPly: %f" % (elapsed_time)  
        
        TimeStart_Lapsed = time.time() - TimeStart
        print "total timw: %f" %(TimeStart_Lapsed)
        #"""
        
        # projection in 2d space to draw it
        rendering =np.zeros((self.Size[0], self.Size[1], 3), dtype = np.uint8)
        # projection of the current image/ Overlay
        #rendering = self.RGBD.Draw_optimize(rendering,Id4, 1, self.color_tag)
        
        for bp in range(1,nbBdyPart):
            for i in range(4):
                for j in range(4):
                    self.PoseBP[i][j] = self.Tg[bp][i][j]
            rendering = self.RGBD.DrawMesh(rendering,self.Vertices[bp],self.Normales[bp],self.PoseBP, 1, self.color_tag)
   
        # 3D reconstruction of the whole image
        self.canvas = tk.Canvas(self, bg="black", height=self.Size[0], width=self.Size[1])
        self.canvas.pack()        
        #rendering = self.DrawColors2D(self.RGBD,rendering,self.Pose)
        img = Image.fromarray(rendering, 'RGB')
        self.imgTk=ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.imgTk)
        #self.DrawSkeleton2D(self.Pose)
        #self.DrawCenters2D(self.Pose)
        #self.DrawSys2D(self.Pose)
        #self.DrawOBBox2D(self.Pose)      

        #enable keyboard and mouse monitoring
        self.root.bind("<Key>", self.key)
        self.root.bind("<Button-1>", self.mouse_press)
        self.root.bind("<ButtonRelease-1>", self.mouse_release)
        self.root.bind("<B1-Motion>", self.mouse_motion)

        self.w = tk.Scale(master, from_=1, to=10, orient=tk.HORIZONTAL)
        self.w.pack()
        

