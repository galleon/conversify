'use client';

import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  AlertCircle,
  CheckCircle,
  Eye,
  File,
  FileImage,
  FileJson,
  FileSpreadsheet,
  FileText,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface UploadedFile {
  file_id: string;
  filename: string;
  file_type: string;
  text_length: number;
  chunks_count: number;
  participant_identity?: string;
  created_at?: string;
}

interface FileUploadError {
  message: string;
  type: 'error' | 'warning' | 'info';
}

interface FileUploadProps {
  participantIdentity?: string;
  onUploadComplete?: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxFileSize?: number; // in MB
  className?: string;
}

const SUPPORTED_TYPES = {
  '.txt': { icon: FileText, color: 'bg-blue-100 text-blue-800' },
  '.md': { icon: FileText, color: 'bg-blue-100 text-blue-800' },
  '.pdf': { icon: File, color: 'bg-red-100 text-red-800' },
  '.docx': { icon: FileText, color: 'bg-blue-100 text-blue-800' },
  '.doc': { icon: FileText, color: 'bg-blue-100 text-blue-800' },
  '.json': { icon: FileJson, color: 'bg-green-100 text-green-800' },
  '.csv': { icon: FileSpreadsheet, color: 'bg-yellow-100 text-yellow-800' },
  '.xlsx': { icon: FileSpreadsheet, color: 'bg-green-100 text-green-800' },
  '.xls': { icon: FileSpreadsheet, color: 'bg-green-100 text-green-800' },
  '.rtf': { icon: FileText, color: 'bg-purple-100 text-purple-800' },
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export function FileUpload({
  participantIdentity,
  onUploadComplete,
  maxFiles = 5,
  maxFileSize = 10,
  className,
}: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errors, setErrors] = useState<FileUploadError[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Load existing files on component mount
  const loadExistingFiles = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const params = new URLSearchParams();
      if (participantIdentity) {
        params.append('participant_identity', participantIdentity);
      }

      const response = await fetch(`${API_BASE_URL}/api/upload/files?${params}`);
      if (response.ok) {
        const data = await response.json();
        setUploadedFiles(data.files || []);
      }
    } catch (error) {
      console.error('Failed to load existing files:', error);
      setErrors([{ message: 'Failed to load existing files', type: 'warning' }]);
    } finally {
      setLoadingFiles(false);
    }
  }, [participantIdentity]);

  // Load existing files when component mounts or participant changes
  useEffect(() => {
    loadExistingFiles();
  }, [loadExistingFiles]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (uploadedFiles.length + acceptedFiles.length > maxFiles) {
        setErrors([
          {
            message: `Cannot upload more than ${maxFiles} files`,
            type: 'error',
          },
        ]);
        return;
      }

      setUploading(true);
      setUploadProgress(0);
      setErrors([]);

      const newUploadedFiles: UploadedFile[] = [];

      try {
        for (let i = 0; i < acceptedFiles.length; i++) {
          const file = acceptedFiles[i];

          // Check file size
          if (file.size > maxFileSize * 1024 * 1024) {
            setErrors((prev) => [
              ...prev,
              {
                message: `${file.name} is too large (max ${maxFileSize}MB)`,
                type: 'error',
              },
            ]);
            continue;
          }

          // Check file type
          const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
          if (!SUPPORTED_TYPES[fileExt as keyof typeof SUPPORTED_TYPES]) {
            setErrors((prev) => [
              ...prev,
              {
                message: `${file.name} has unsupported file type`,
                type: 'error',
              },
            ]);
            continue;
          }

          const formData = new FormData();
          formData.append('file', file);
          if (participantIdentity) {
            formData.append('participant_identity', participantIdentity);
          }

          try {
            const response = await fetch(`${API_BASE_URL}/api/upload/file`, {
              method: 'POST',
              body: formData,
            });

            if (response.ok) {
              const result = await response.json();
              if (result.success) {
                newUploadedFiles.push(result.data);
              } else {
                setErrors((prev) => [
                  ...prev,
                  {
                    message: `Failed to upload ${file.name}: ${result.message}`,
                    type: 'error',
                  },
                ]);
              }
            } else {
              const errorData = await response.json();
              setErrors((prev) => [
                ...prev,
                {
                  message: `Failed to upload ${file.name}: ${errorData.detail || 'Unknown error'}`,
                  type: 'error',
                },
              ]);
            }
          } catch (error) {
            setErrors((prev) => [
              ...prev,
              {
                message: `Failed to upload ${file.name}: Network error`,
                type: 'error',
              },
            ]);
          }

          // Update progress
          setUploadProgress(((i + 1) / acceptedFiles.length) * 100);
        }

        if (newUploadedFiles.length > 0) {
          const updatedFiles = [...uploadedFiles, ...newUploadedFiles];
          setUploadedFiles(updatedFiles);
          onUploadComplete?.(updatedFiles);

          setErrors((prev) => [
            ...prev,
            {
              message: `Successfully uploaded ${newUploadedFiles.length} file(s)`,
              type: 'info',
            },
          ]);
        }
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    },
    [uploadedFiles, maxFiles, maxFileSize, participantIdentity, onUploadComplete]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/json': ['.json'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/rtf': ['.rtf'],
    },
    multiple: true,
    disabled: uploading || uploadedFiles.length >= maxFiles,
  });

  const deleteFile = async (fileId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload/files/${fileId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const updatedFiles = uploadedFiles.filter((f) => f.file_id !== fileId);
        setUploadedFiles(updatedFiles);
        onUploadComplete?.(updatedFiles);
        setErrors([{ message: 'File deleted successfully', type: 'info' }]);
      } else {
        const errorData = await response.json();
        setErrors([{ message: `Failed to delete file: ${errorData.detail}`, type: 'error' }]);
      }
    } catch (error) {
      setErrors([{ message: 'Failed to delete file: Network error', type: 'error' }]);
    }
  };

  const getFileIcon = (fileType: string) => {
    const typeInfo = SUPPORTED_TYPES[fileType as keyof typeof SUPPORTED_TYPES];
    const IconComponent = typeInfo?.icon || File;
    return <IconComponent className="h-4 w-4" />;
  };

  const getFileTypeColor = (fileType: string) => {
    return (
      SUPPORTED_TYPES[fileType as keyof typeof SUPPORTED_TYPES]?.color ||
      'bg-gray-100 text-gray-800'
    );
  };

  const clearErrors = () => setErrors([]);

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Background Knowledge
        </CardTitle>
        <CardDescription>
          Upload documents to provide background knowledge to the AI agent. Supported formats: TXT,
          MD, PDF, DOCX, JSON, CSV, XLSX, RTF (max {maxFileSize}MB each)
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Error/Success Messages */}
        {errors.length > 0 && (
          <div className="space-y-2">
            {errors.map((error, index) => (
              <Alert key={index} variant={error.type === 'error' ? 'destructive' : 'default'}>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  {error.message}
                  <Button variant="ghost" size="sm" onClick={clearErrors} className="h-auto p-1">
                    <XCircle className="h-3 w-3" />
                  </Button>
                </AlertDescription>
              </Alert>
            ))}
          </div>
        )}

        {/* Upload Area */}
        {uploadedFiles.length < maxFiles && (
          <div
            {...getRootProps()}
            className={cn(
              'cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors',
              isDragActive
                ? 'border-primary bg-primary/10'
                : 'border-gray-300 hover:border-gray-400',
              uploading && 'cursor-not-allowed opacity-50'
            )}
          >
            <input {...getInputProps()} />

            <Upload className="mx-auto mb-4 h-12 w-12 text-gray-400" />

            {isDragActive ? (
              <p className="text-lg font-medium">Drop files here...</p>
            ) : (
              <>
                <p className="mb-2 text-lg font-medium">
                  {uploading ? 'Uploading...' : 'Drag & drop files here'}
                </p>
                <p className="mb-4 text-sm text-gray-500">
                  or click to select files ({uploadedFiles.length}/{maxFiles} used)
                </p>
                <Button variant="outline" disabled={uploading}>
                  Select Files
                </Button>
              </>
            )}
          </div>
        )}

        {/* Upload Progress */}
        {uploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Uploading files...</span>
              <span>{Math.round(uploadProgress)}%</span>
            </div>
            <Progress value={uploadProgress} className="w-full" />
          </div>
        )}

        {/* Uploaded Files List */}
        {(uploadedFiles.length > 0 || loadingFiles) && (
          <div className="space-y-2">
            <h4 className="font-medium">Uploaded Files ({uploadedFiles.length})</h4>

            {loadingFiles ? (
              <div className="py-4 text-center text-sm text-gray-500">
                Loading existing files...
              </div>
            ) : (
              <ScrollArea className="max-h-60">
                <div className="space-y-2">
                  {uploadedFiles.map((file) => (
                    <div
                      key={file.file_id}
                      className="flex items-center justify-between rounded-lg bg-gray-50 p-3"
                    >
                      <div className="flex min-w-0 flex-1 items-center space-x-3">
                        <div className="flex-shrink-0">{getFileIcon(file.file_type)}</div>

                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{file.filename}</p>
                          <div className="mt-1 flex items-center space-x-2">
                            <Badge variant="secondary" className={getFileTypeColor(file.file_type)}>
                              {file.file_type.toUpperCase()}
                            </Badge>
                            <span className="text-xs text-gray-500">
                              {file.text_length.toLocaleString()} chars
                            </span>
                            {file.chunks_count > 0 && (
                              <span className="text-xs text-gray-500">
                                {file.chunks_count} chunks
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteFile(file.file_id)}
                          className="text-red-600 hover:bg-red-50 hover:text-red-800"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        )}

        {/* Upload Status */}
        {uploadedFiles.length === maxFiles && (
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              Maximum number of files reached ({maxFiles}/{maxFiles}). Delete some files to upload
              more.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default FileUpload;
