#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon May  1 13:38:34 2017

@author: diegothomas
"""


import imp
import numpy as np
import pyopencl as cl
import math
import time
PI = math.pi
GPU = imp.load_source('GPUManager', './lib/GPUManager.py')
KernelsOpenCL = imp.load_source('MarchingCubes_KernelOpenCL', './lib/MarchingCubes_KernelOpenCL.py')
General = imp.load_source('General', './lib/General.py')

mf = cl.mem_flags

class My_MarchingCube():
    
    def __init__(self, Size, Res, Iso, GPUManager):
        self.Size = Size
        self.res = Res
        self.iso = Iso
        self.nb_faces = np.array([0], dtype = np.int32)
        
        self.GPUManager = GPUManager
        
        self.GPUManager.programs['MarchingCubesIndexing'] = cl.Program(self.GPUManager.context, KernelsOpenCL.Kernel_MarchingCubeIndexing).build()
        self.GPUManager.programs['MarchingCubes'] = cl.Program(self.GPUManager.context, KernelsOpenCL.Kernel_MarchingCube).build()
        
        
        self.Size_Volume = cl.Buffer(self.GPUManager.context, mf.READ_ONLY | mf.COPY_HOST_PTR, \
                               hostbuf = np.array([self.Size[0], self.Size[1], self.Size[2]], dtype = np.int32))
        
        tmp = np.zeros(self.Size, dtype = np.int32)
        self.OffsetGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, tmp.nbytes)
        self.IndexGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, tmp.nbytes)
        self.FaceCounterGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf = self.nb_faces)
        
        self.ParamGPU = cl.Buffer(self.GPUManager.context, mf.READ_ONLY | mf.COPY_HOST_PTR, \
                               hostbuf = self.res)
        
        
    def runGPU(self, VolGPU):
        
        self.nb_faces[0] = 0
        cl.enqueue_write_buffer(self.GPUManager.queue, self.FaceCounterGPU, self.nb_faces).wait()
        self.GPUManager.programs['MarchingCubesIndexing'].MarchingCubesIndexing(self.GPUManager.queue, (self.Size[0]-1, self.Size[1]-1), None, \
                                VolGPU, self.OffsetGPU, self.IndexGPU, self.Size_Volume, np.int32(self.iso), self.FaceCounterGPU).wait()
        
        
        cl.enqueue_read_buffer(self.GPUManager.queue, self.FaceCounterGPU, self.nb_faces).wait()
        print "nb Faces: ", self.nb_faces[0]
        
        self.Faces = np.zeros((self.nb_faces[0], 3), dtype = np.int32)
        self.Vertices = np.zeros((3*self.nb_faces[0], 3), dtype = np.float32)
        
        self.FacesGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.Faces.nbytes)
        self.VerticesGPU = cl.Buffer(self.GPUManager.context, mf.READ_WRITE, self.Vertices.nbytes)

        
        self.GPUManager.programs['MarchingCubes'].MarchingCubes(self.GPUManager.queue, (self.Size[0]-1, self.Size[1]-1), None, \
                                VolGPU, self.OffsetGPU, self.IndexGPU, self.VerticesGPU, self.FacesGPU, self.ParamGPU, self.Size_Volume).wait()
        
        cl.enqueue_read_buffer(self.GPUManager.queue, self.VerticesGPU, self.Vertices).wait()
        cl.enqueue_read_buffer(self.GPUManager.queue, self.FacesGPU, self.Faces).wait()

        self.MergeVtx()



    ''' 
    Function to record the created mesh into a .ply file
    '''
    def SaveToPly(self, name, save = 0):
        if save != 0:
            start_time3 = time.time()
        path = './meshes/'
        f = open(path+name, 'wb')
        
        # Write headers
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write("comment ply file created by Diego Thomas\n")
        f.write("element vertex %d \n" %(self.nb_vertices[0]))
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("element face %d \n" %(self.nb_faces[0]))
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")
        
        # Write vertices
        for i in range(self.nb_vertices[0]):
            f.write("%f %f %f \n" %(self.Vertices[i,0], self.Vertices[i,1], self.Vertices[i,2]))
            
        # Write the faces
        for i in range(self.nb_faces[0]):
            f.write("3 %d %d %d \n" %(self.Faces[i,0], self.Faces[i,1], self.Faces[i,2])) 
                     
        f.close()

        if save != 0:
            elapsed_time = time.time() - start_time3
            print "SaveToPly: %f" % (elapsed_time)
                    
    '''
        Function to record an external created mesh into a .ply file 
    '''
    def SaveToPlyExt(self, name,nb_vertices,nb_faces,Vertices,Faces,save = 0):
        if save != 0:
            start_time3 = time.time()
        path = './meshes/'
        f = open(path+name, 'wb')
        
        # Write headers
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write("comment ply file created by Diego Thomas\n")
        f.write("element vertex %d \n" %(nb_vertices))
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("element face %d \n" %(nb_faces))
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")
        
        # Write vertices
        for i in range(nb_vertices):
            f.write("%f %f %f \n" %(Vertices[i,0], Vertices[i,1], Vertices[i,2]))
            
        # Write the faces
        for i in range(nb_faces):
            f.write("3 %d %d %d \n" %(Faces[i,0], Faces[i,1], Faces[i,2])) 
                     
        f.close()

        if save != 0:
            elapsed_time = time.time() - start_time3
            print "SaveToPly: %f" % (elapsed_time)
        
                    
    '''
        Function to draw the mesh using tkinter
    '''
    def DrawMesh(self, Pose, intrinsic, Size, canvas):
        
        #Draw all faces
        pix = np.array([0., 0., 1.])
        pt = np.array([0., 0., 0., 1.])
        for i in range(self.nb_faces[0]):
            inviewingvolume = False
            poly = []
            for k in range(3):
                pt[0] = self.Vertices[self.Faces[i,k],0]
                pt[1] = self.Vertices[self.Faces[i,k],1]
                pt[2] = self.Vertices[self.Faces[i,k],2]
                pt = np.dot(Pose, pt)
                pix[0] = pt[0]/pt[2]
                pix[1] = pt[1]/pt[2]
                pix = np.dot(intrinsic, pix)
                column_index = int(round(pix[0]))
                line_index = int(round(pix[1]))
                poly.append((column_index, line_index))
                    
                if (column_index > -1 and column_index < Size[1] and line_index > -1 and line_index < Size[0]):
                    inviewingvolume = True
                    
            if inviewingvolume:
                canvas.create_polygon(*poly, fill='white')
                    
                
    '''
        Function to draw the vertices of the mesh using tkinter
    '''
    def DrawPoints(self, Pose, intrinsic, Size,background,s=1):
        #result = np.zeros((Size[0], Size[1], 3), dtype = np.uint8)
        result = background.astype(np.uint8)
        
        pt = np.ones(((np.size(self.Vertices, 0)-1)/s+1, np.size(self.Vertices, 1)+1))
        pt[:,:-1] = self.Vertices[::s, :]
        pt = np.dot(Pose,pt.transpose()).transpose()
        #nmle = np.zeros((self.Size[0], self.Size[1],self.Size[2]), dtype = np.float32)
        #nmle[ ::s, ::s,:] = np.dot(Pose[0:3,0:3],self.Nmls[ ::s, ::s,:].transpose(0,2,1)).transpose(1,2,0)
        
        pix = np.ones(((np.size(self.Vertices, 0)-1)/s+1, np.size(self.Vertices, 1)))
        pix[:,0] = pt[:,0]/pt[:,2]
        pix[:,1] = pt[:,1]/pt[:,2]
        pix = np.dot(intrinsic,pix.transpose()).transpose()
        
        column_index = (np.round(pix[:,0])).astype(int)
        line_index = (np.round(pix[:,1])).astype(int)
        # create matrix that have 0 when the conditions are not verified and 1 otherwise
        cdt_column = (column_index > -1) * (column_index < Size[1]) * pt[:,2] > 0.0
        cdt_line = (line_index > -1) * (line_index < Size[0]) * pt[:,2] > 0.0
        line_index = line_index*cdt_line
        column_index = column_index*cdt_column
        result[line_index[:], column_index[:]]= 255*np.ones((np.size(pix, 0), 3), dtype = np.uint8)
        return result
                    

    '''
        Function to compute the normals of the mesh 
    '''
    def TransformList(self, Pose):
        stack_pt = np.ones(np.size(self.Vertices,0), dtype = np.float32)
        pt = np.stack((self.Vertices[:,0],self.Vertices[:,1],self.Vertices[:,2], stack_pt),axis =1)
        self.Vertices = np.dot(Pose,pt.T).T[:, 0:3]
        self.Normales = np.dot(Pose[0:3,0:3],self.Normales.T).T                      
                    
    '''
        Function to compute the normals of the mesh 
    '''
    def ComputeMCNmls(self):
        
        # instanciation
        nb_faces = self.nb_faces[0]
        vectsFaces = np.zeros((2,nb_faces, 3), dtype = np.float)
        facesNmls = np.zeros((nb_faces, 3), dtype = np.float)
        
        # edges of triangles
        vectsFaces[0,:,:] = self.Vertices[self.Faces[:,1]]-self.Vertices[self.Faces[:,0]]   
        vectsFaces[1,:,:] = self.Vertices[self.Faces[:,2]]-self.Vertices[self.Faces[:,0]]

        # compute each face's normal
        facesNmls[:,0] = vectsFaces[0,:,1]*vectsFaces[1,:,2]- vectsFaces[0,:,2]*vectsFaces[1,:,1]
        facesNmls[:,1] = vectsFaces[0,:,2]*vectsFaces[1,:,0]- vectsFaces[0,:,0]*vectsFaces[1,:,2]
        facesNmls[:,2] = vectsFaces[0,:,0]*vectsFaces[1,:,1]- vectsFaces[0,:,1]*vectsFaces[1,:,0]
        self.Normals[self.Faces[:,0]] += facesNmls
        self.Normals[self.Faces[:,1]] += facesNmls
        self.Normals[self.Faces[:,2]] += facesNmls

        
        # compute the norm of nmlsSum
        norm_nmlsSum = np.sqrt(np.sum(self.Normals*self.Normals,axis=1))
        norm_nmlsSum = General.in_mat_zero2one(norm_nmlsSum)
        # normalize the mean of the norm
        self.Normals = division_by_norm(self.Normals,norm_nmlsSum)


    '''
    Non optimized version for understanding
    THIS FUNCTION IS NOT USED
    '''
    def ComputeMCNmls_slow(self):
        # instanciation
        nb_faces = self.nb_faces[0]
        vectsFaces = np.zeros((2, 3), dtype = np.int32)

        for f in range(nb_faces):
            # vectors of triangles
            vectsFaces[0,:] = self.Vertices[self.Faces[f,1]]-self.Vertices[self.Faces[f,0]]
            vectsFaces[1,:] = self.Vertices[self.Faces[f,2]]-self.Vertices[self.Faces[f,0]]

            # compute each face's normal
            facesNmls = np.cross(vectsFaces[1,:],vectsFaces[0,:])
            for s in range(3):
                # sum of normals
                self.Normals[self.Faces[f,s]] += facesNmls

        for v in range(self.Normals.shape[0]):
            # compute the norm of normals
            norm_nmlsSum = np.sqrt(np.sum(self.Normals[v]*self.Normals[v]))
            if norm_nmlsSum == 0:
                continue
            # normalize the normals
            self.Normals[v] = self.Normals[v]/norm_nmlsSum


    '''
    This function avoid having duplicate in the lists of vertexes or normales
    THIS METHOD HAVE A GPU VERSION BUT THE GPU HAVE NOT ENOUGH MEMORY TO RUN IT
    '''
    def MergeVtx(self):
        VtxArray_x = np.zeros(self.Size)
        VtxArray_y = np.zeros(self.Size)
        VtxArray_z = np.zeros(self.Size)
        VtxWeights = np.zeros(self.Size)
        VtxIdx = np.zeros(self.Size)
        FacesIdx = np.zeros((self.nb_faces[0], 3, 3), dtype = np.uint16)
        self.Normales = np.zeros((3*self.nb_faces[0], 3), dtype = np.float32)
        # Go through all faces
        pt = np.array([0., 0., 0., 1.])
        self.nbVtx = 0
        for i in range(self.nb_faces[0]):
            for k in range(3):
                pt[0] = self.Vertices[self.Faces[i,k],0]
                pt[1] = self.Vertices[self.Faces[i,k],1]
                pt[2] = self.Vertices[self.Faces[i,k],2]
                indx = (int(round(pt[0]*self.res[1]+self.res[0])), 
                        int(round(pt[1]*self.res[3]+self.res[2])), 
                        int(round(pt[2]*self.res[5]+self.res[4])))
                if (VtxWeights[indx] == 0):
                    self.nbVtx += 1
                VtxArray_x[indx] = (VtxWeights[indx]*VtxArray_x[indx] + pt[0])/(VtxWeights[indx]+1)
                VtxArray_y[indx] = (VtxWeights[indx]*VtxArray_y[indx] + pt[1])/(VtxWeights[indx]+1)
                VtxArray_z[indx] = (VtxWeights[indx]*VtxArray_z[indx] + pt[2])/(VtxWeights[indx]+1)
                VtxWeights[indx] = VtxWeights[indx]+1
                FacesIdx[i,k,0] = indx[0]
                FacesIdx[i,k,1] = indx[1]
                FacesIdx[i,k,2] = indx[2]
                       
        print "nb vertices: ", self.nbVtx
        self.nb_vertices = np.array([self.nbVtx], dtype = np.int32)
        self.Vertices = np.zeros((self.nbVtx, 3), dtype = np.float32)
        self.Normales = np.zeros((self.nbVtx, 3), dtype = np.float32)
        index_count = 0
        for i in range(self.Size[0]):
            #print i
            for j in range(self.Size[1]):
                for k in range(self.Size[2]):
                    if (VtxWeights[i,j,k] > 0):
                        VtxIdx[i,j,k] = index_count
                        self.Vertices[index_count, 0] = VtxArray_x[i,j,k]
                        self.Vertices[index_count, 1] = VtxArray_y[i,j,k]
                        self.Vertices[index_count, 2] = VtxArray_z[i,j,k]
                        index_count += 1 
        
        for i in range(self.nb_faces[0]):
            v = np.zeros((3, 3), dtype = np.float32)
            for k in range(3):
                self.Faces[i,k] = VtxIdx[(FacesIdx[i,k,0],FacesIdx[i,k,1],FacesIdx[i,k,2])]
                v[k,:] = self.Vertices[self.Faces[i,k],:]
            
            v1 = v[1,:] - v[0,:]
            v2 = v[2,:] - v[0,:]
            nmle = [v1[1]*v2[2] - v1[2]*v2[1],
                    -v1[0]*v2[2] + v1[2]*v2[0],
                    v1[0]*v2[1] - v1[1]*v2[0]]
            
            for k in range(3):
                self.Normales[self.Faces[i,k], :] = self.Normales[self.Faces[i,k],:] + nmle
        
        
        for i in range(self.nb_vertices[0]):
            mag = math.sqrt(self.Normales[i, 0]**2 + self.Normales[i, 1]**2 + self.Normales[i, 2]**2)
            if mag == 0.0:
                self.Normales[i, :] = 0.0
            else :
                self.Normales[i, :] = self.Normales[i, :]/mag
        
        

        
    '''
        Function to convert the list of normales and vertexes of the marching cubes' algorithm into
        424*512*3 matrix.
        This function is made just to test with the RegisterRGBD function if the data from the mesh are corrects.
    '''        
    def MC2RGBD(self,RGBD,Vtx,Nmls,Pose, s, color = 0) :   
        result = np.zeros((RGBD.Size[0], RGBD.Size[1], 3), dtype = np.uint8)#
        stack_pix = np.ones( (np.size(Vtx[ ::s,:],0)) , dtype = np.float32)
        stack_pt = np.ones( (np.size(Vtx[ ::s,:],0)) , dtype = np.float32)
        pix = np.zeros( (np.size(Vtx[ ::s,:],0),2) , dtype = np.float32)
        pix = np.stack((pix[:,0],pix[:,1],stack_pix),axis = 1)
        pt = np.stack( (Vtx[ ::s,0],Vtx[ ::s,1],Vtx[ ::s,2],stack_pt),axis =1 )
        pt = np.dot(Pose,pt.T).T

        nmle = np.zeros((Nmls.shape[0], Nmls.shape[1]), dtype = np.float32)
        nmle[ ::s,:] = np.dot(Pose[0:3,0:3],Nmls[ ::s,:].T).T
        

        # projection in 2D space
        lpt = np.split(pt,4,axis=1)
        lpt[2] = General.in_mat_zero2one(lpt[2])
        pix[ ::s,0] = (lpt[0]/lpt[2]).reshape(np.size(Vtx[ ::s,:],0))
        pix[ ::s,1] = (lpt[1]/lpt[2]).reshape(np.size(Vtx[ ::s,:],0))
        pix = np.dot(pix,RGBD.intrinsic.T)

        column_index = (np.round(pix[:,0])).astype(int)
        line_index = (np.round(pix[:,1])).astype(int)
        # create matrix that have 0 when the conditions are not verified and 1 otherwise
        cdt_column = (column_index > -1) * (column_index < RGBD.Size[1])
        cdt_line = (line_index > -1) * (line_index < RGBD.Size[0])
        line_index = line_index*cdt_line
        column_index = column_index*cdt_column

        # print "max line_index : %d" %(np.max(line_index))
        # print "max column_index : %d" %(np.max(column_index))
        # print "argmax line_index : %d" %(np.argmax(line_index))
        # print "argmax column_index : %d" %(np.argmax(column_index))
        # print "line_index24 : %d" %(line_index[24])
        # print "column_index24 : %d" %(column_index[24])

        if (color == 1):
            result[line_index[:], column_index[:]]= np.dstack((RGBD.color_image[ ::s, ::s,2], \
                                                                    RGBD.color_image[ ::s, ::s,1]*cdt_line, \
                                                                    RGBD.color_image[ ::s, ::s,0]*cdt_column) )
        else:
            RGBD.Nmls[line_index[:], column_index[:]]= np.dstack( ( nmle[ :,0], nmle[ :,1], nmle[ :,2]) )
            RGBD.Vtx[line_index[:], column_index[:]] = np.dstack( ( pt[ :,0], pt[ :,1], pt[ :,2]) )
            RGBD.depth_image[line_index[:], column_index[:]] =  pt[ :,2] 


