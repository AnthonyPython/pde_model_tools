# mesh_prop\utils.py
import struct
import traceback

from .. import tools
from ..log import log


# Define function to read mesh header
def read_head(self, data, start_index):
    """Read mesh header"""
    log.debug(">>> Begin reading mesh header: %s", hex(start_index))

    # Ensure there are enough bytes for unpacking
    if len(data) < start_index + 0x1D:
        log.debug("! Failed to parse header: insufficient bytes at offset %s", hex(start_index))
        self.report({"ERROR"}, "Header parsing failed")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("start_index: %s", hex(start_index))
    # Number of mesh objects (only the first file uses this)
    mesh_obj_number = struct.unpack_from("<I", data, start_index)[0]
    # Face group count
    mesh_face_group_number = struct.unpack_from("<I", data, start_index + 4)[0]
    # Matrix count
    mesh_matrices_number = struct.unpack_from("<I", data, start_index + 8)[0]
    # 4-byte 00 flag (unused)
    # zeros_tag = struct.unpack_from("<I", data, 36)[0]
    # 1-byte 01 flag (unused)
    # zeroone_tag = struct.unpack_from("<B", data, 48)[0]
    # Total bytes of this mesh
    mesh_byte_size = struct.unpack_from("<I", data, start_index + 25)[0]

    # Print header info
    log.debug(
        "<<< mesh objects: %s face groups: %s matrices: %s byte size: %s",
        hex(mesh_obj_number), hex(mesh_face_group_number), hex(mesh_matrices_number), hex(mesh_byte_size)
    )

    # Return mesh object count, face group count, matrix count and byte size
    return mesh_obj_number, mesh_face_group_number, mesh_matrices_number, mesh_byte_size


# Parse vertex data
def read_vertices(self, vertices_data, mesh_matrices_number, mesh_byte_size):
    """Parse vertex data"""
    log.debug(">>> Begin parsing vertex data")
    # Vertex array
    vertices = []
    # Normal array
    normals = []
    # UV coordinate array
    uvs = []

    # Size of each data block (0x34)
    block_size = int(mesh_byte_size / mesh_matrices_number)
    if block_size <= 0:
        log.debug("! Failed to compute block size: %s", hex(block_size))
        self.report({"ERROR"}, "Block size calculation failed")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("> Block size: %s", hex(block_size))

    # 解析顶点数据
    try:
        for mni in range(mesh_matrices_number):
            # Calculate start of current block
            mniv = block_size * mni
            # Ensure there are enough bytes to unpack
            if mniv + block_size <= mesh_byte_size:
                vx = struct.unpack_from("f", vertices_data, mniv)[0]
                vy = struct.unpack_from("f", vertices_data, mniv + 4)[0]
                vz = struct.unpack_from("f", vertices_data, mniv + 8)[0]
                # Append vertex to list
                vertices.append((vx, vy, vz))

                # Read normal data
                nx = tools.read_half_float(vertices_data, mniv + 0x0c)
                ny = tools.read_half_float(vertices_data, mniv + 0x0e)
                nz = tools.read_half_float(vertices_data, mniv + 0x10)
                normals.append((nx, ny, nz))
                # log.debug(">> Read normal data: %s , %s , %s", nx, ny, nz)

                # Read UV coordinates
                # TODO: verify UV mapping (possible bug)
                uv_start = mniv + block_size - 0xc
                # log.debug(">> uv_start: %s , mniv : %s ", uv_start, mniv)
                u = tools.read_half_float(vertices_data, uv_start)
                v = tools.read_half_float(vertices_data, uv_start + 0x2)
                uvs.append((u, 1 - v))
                log.debug(">> Read UV coordinates: %s , %s ", u, 1 - v)
            else:
                log.debug("! Vertex data parse failed: insufficient bytes at offset %s", mniv)
                break
    except Exception as e:
        log.debug("! Vertex data parse failed: %s", e)
        self.report({"ERROR"}, f"Vertex data parse failed: {e}")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("<<< Vertex data parsed: %s groups", len(vertices))

    return vertices, normals, uvs


# Parse face data
def read_faces(self, faces_data_block, index_length):
    """Parse face data"""
    log.debug(">>> Begin parsing face data %s", index_length)
    faces = []
    try:
        # Ensure there are enough bytes to unpack
        for i in range(0, index_length, 12):
            f0 = struct.unpack_from("H", faces_data_block, i)[0]
            f1 = struct.unpack_from("H", faces_data_block, i + 4)[0]
            f2 = struct.unpack_from("H", faces_data_block, i + 8)[0]
            faces.append((f0, f1, f2))
            # log.debug("> Parsing face: %s -> %s %s %s", i, f0, f1, f2)
    except Exception as e:
        log.debug("! Face data parse failed: %s", e)
        self.report({"ERROR"}, f"Face data parse failed: {e}")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("<<< Finished reading %s faces", hex(len(faces)))

    return faces


# Split mesh data
def split_mesh(self, data):
    """Split mesh data"""
    log.debug(">>> Begin splitting mesh data")

    # Data start offset
    data_start = 0
    # Is this the first read
    first_read = True
    # Mesh objects
    mesh_obj = []

    try:
        while True:
            if first_read:
                data_start += 24
                first_read = False

            # Read header -> returns mesh object count, face group count, matrix count, and byte size
            (
                mesh_obj_number,
                mesh_face_group_number,
                mesh_matrices_number,
                mesh_byte_size,
            ) = read_head(self, data, data_start)

            # Get vertex data length
            vertices_data = data[data_start + 0x1D: data_start + 0x1D + mesh_byte_size]
            log.debug("> Vertex data length: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! Failed to get vertex data length")
                self.report({"ERROR"}, "Failed to get vertex data length")
                traceback.print_exc()
                return {"CANCELLED"}

            # 解析顶点数据块
            vertices_array, normals, uvs = read_vertices(
                self, vertices_data, mesh_matrices_number, mesh_byte_size
            )

            # 获取面数据块大小
            faces_data_size = struct.unpack(
                "<I",
                data[
                data_start
                + 0x1D
                + mesh_byte_size: data_start
                                  + 0x1D
                                  + mesh_byte_size
                                  + 4
                ],
            )[0]
            log.debug("> Face block size: %s", hex(faces_data_size))
            # 获取面数据块
            faces_data_block = data[
                               data_start
                               + 0x1D
                               + mesh_byte_size
                               + 4: data_start
                                    + 0x1D
                                    + mesh_byte_size
                                    + 4
                                    + faces_data_size
                               ]
            log.debug("> Index address: %s", hex(data_start + 0x1d + mesh_byte_size + 4))
            log.debug("> Face data block length: %s", hex(len(faces_data_block)))
            # 解析面数据块
            faces_array = read_faces(self, faces_data_block, len(faces_data_block))

            # Append data to mesh_obj
            mesh_obj.append(
                {
                    "vertices": {
                        "mesh_obj_number": mesh_obj_number,
                        "mesh_matrices_number": mesh_matrices_number,
                        "mesh_byte_size": mesh_byte_size,
                        "data": vertices_array,
                    },
                    "faces": {"size": faces_data_size, "data": faces_array},
                    "uvs": uvs,
                    "normals": normals,
                }
            )

            # End position, also the new start
            data_start += 0x1D + mesh_byte_size + 4 + faces_data_size
            log.debug("> data_start: %s", hex(data_start))

            # Check if end of file reached
            if len(mesh_obj) >= mesh_obj[0]["vertices"]["mesh_obj_number"] - 1:
                log.debug("<<< Reached end of data")
                break

        return mesh_obj
    except Exception as e:
        log.debug("! Failed to split mesh data: %s", e)
        self.report({"ERROR"}, f"Failed to split mesh data: {e}")
        traceback.print_exc()
        return {"CANCELLED"}
