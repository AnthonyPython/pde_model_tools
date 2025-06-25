# mesh_wcm\utils.py
import struct
import traceback

from .. import tools
from ..log import log


def read_dynamic_head(self, data):
    """Read the dynamic header"""
    log.debug(">>> Begin reading header")

    try:
        # Mesh info
        mesh_info = []
        # Read position
        data_index = 0
        # Number of included objects 1
        include_obj_number1 = struct.unpack_from("<I", data, data_index)[0]
        # Advance index
        data_index += 4

        # Read included object names
        for i in range(include_obj_number1):
            # Read object name length
            name_length = struct.unpack_from("<I", data, data_index)[0]
            # Advance index
            data_index += 4
            # Read object name
            obj_name = struct.unpack_from(f"<{name_length}s", data, data_index)[
                0
            ].decode("utf-8")
            log.debug("Object name: %s", obj_name)
            # Save name
            mesh_info.append(obj_name)
            # Advance index
            data_index += name_length

        # Number of included objects 2
        include_obj_number2 = struct.unpack_from("<I", data, data_index)[0]
        # Advance index
        data_index += 4

        # Check if header counts match
        if include_obj_number1 != include_obj_number2:
            log.debug("! Header parse failed: object counts mismatch")
            self.report({"ERROR"}, "Header parse failed")
            traceback.print_exc()
            return {"CANCELLED"}

        # Skip initial object and camera positions (uncertain)
        skip_len = include_obj_number1 * 0x18
        log.debug("data_index: %s", hex(data_index))

        # Advance index
        data_index += skip_len

        log.debug("data_index: %s skip_len: %s", hex(data_index), hex(skip_len))

        # Return object start position and info
        return data_index, mesh_info
    except Exception as e:
        log.debug("! Failed to read header: %s", e)
        self.report({"ERROR"}, "Failed to read header")
        traceback.print_exc()
        return {"CANCELLED"}


# Function to read mesh header
def read_head(data, start_index):
    """Read mesh header"""
    log.debug(">>> Begin reading header: %s", hex(start_index))

    # Ensure there are enough bytes to unpack
    if len(data) < start_index + 0x1D:
        log.debug("! Header parse failed: insufficient bytes at offset %s", start_index)
        traceback.print_exc()
        return None
        # self.report({"ERROR"}, "头部信息解析失败")
        # return {"CANCELLED"}

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
        "<<< mesh objects: %s face groups %s matrices: %s byte size: %s",
        hex(mesh_obj_number), hex(mesh_face_group_number), hex(mesh_matrices_number), hex(mesh_byte_size)
    )

    # Return mesh object count, face group count, matrix count and byte size
    return mesh_obj_number, mesh_face_group_number, mesh_matrices_number, mesh_byte_size


# Parse vertex data
def read_vertices(self, vertices_data, mesh_matrices_number, mesh_byte_size):
    """Parse vertex data"""
    log.debug(">>> Begin parsing vertex data")
    # Vertex data
    vertices = []
    # Normal data
    normals = []
    # UV coordinate data
    uvs = []

    # Size of each data block (0x34 is an estimate; may need adjustment)
    block_size = int(mesh_byte_size / mesh_matrices_number)
    if block_size <= 0:
        log.debug("! Failed to compute block size: %s", block_size)
        self.report({"ERROR"}, "Block size calculation failed")
        traceback.print_exc()
        return {"CANCELLED"}

    log.debug("> Block size: %s", block_size)

    # 解析顶点数据
    try:
        for mni in range(mesh_matrices_number):
            # Calculate current block start
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
                uv_start = mniv + block_size - 8
                # log.debug(">> uv_start: %s , mniv : %s ", uv_start, mniv)
                u = tools.read_half_float(vertices_data, uv_start)
                v = tools.read_half_float(vertices_data, uv_start + 0x2)
                uvs.append((u, 1 - v))
                # log.debug(">> Read UV coordinates: %s , %s ", u, 1 - v)

            else:
                log.debug("! Vertex data parse failed: insufficient bytes at offset %s", mniv)
                break
    except Exception as e:
        log.debug("! Vertex data parse failed: %s", e)
        # self.report({"ERROR"}, f"顶点数据解析失败 : {e}")
        # traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< Vertex data parsed: %s groups", hex(len(vertices)))
    # Return vertices, normals and UVs
    return vertices, normals, uvs


# Parse face data
def read_faces(self, faces_data_block, index_length):
    """Parse face data"""
    log.debug(">>> Begin parsing face data %s", hex(index_length))
    faces = []
    try:
        # Ensure there are enough bytes to unpack
        for i in range(0, index_length, 12):
            f0 = struct.unpack_from("H", faces_data_block, i)[0]
            f1 = struct.unpack_from("H", faces_data_block, i + 4)[0]
            f2 = struct.unpack_from("H", faces_data_block, i + 8)[0]
            faces.append((f0, f1, f2))
            # log.debug("> Parsing face: %s -> %s %s %s", f0, f1, f2)
    except Exception as e:
        log.debug("! Face data parse failed: %s", e)
        # self.report({"ERROR"}, f"面数据解析失败 : {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< Finished reading %s faces", hex(len(faces)))

    return faces


# Split mesh data
def split_mesh(self, data):
    """Split mesh data"""
    log.debug(">>> Begin splitting mesh data")

    # Data start offset
    data_start = 0
    # Is this the first read
    # first_read = True
    # Mesh objects
    mesh_obj = []

    # Read dynamic header
    data_index, mesh_info = read_dynamic_head(self, data)
    # Adjust data start position
    data_start = data_index
    log.debug("> fix data start: %s", hex(data_start))

    try:
        for mi_name in mesh_info:
            log.debug(">>> Reading mesh info name: %s", mi_name)
            # if first_read:
            #     data_start += 24
            #     first_read = False

            # Read header information
            read_head_temp = read_head(data, data_start)

            if read_head_temp is None:
                log.debug("! Failed to read header")
                # return mesh_obj
                break

            # Returned values: mesh object count, face group count, matrix count and byte size
            (
                mesh_obj_number,
                mesh_face_group_number,
                mesh_matrices_number,
                mesh_byte_size,
            ) = read_head_temp

            # Get vertex data length
            vertices_data = data[data_start + 0x1D: data_start + 0x1D + mesh_byte_size]
            log.debug("> Vertex data length: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! Failed to get vertex data length")
                # self.report({"ERROR"}, "获取顶点数据长度失败")
                # traceback.print_exc()
                # return {"CANCELLED"}
                break

            # Parse vertex data block
            read_vertices_temp = read_vertices(
                self, vertices_data, mesh_matrices_number, mesh_byte_size
            )
            # Check for parse failure
            if read_vertices_temp is None:
                log.debug("! Failed to parse vertex data")
                # return mesh_obj
                break
            # Vertex data, UV data, tangents
            vertices_array, normals, uvs = read_vertices_temp

            # Get face data block size
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
            # Get face data block
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
            # Parse face data block
            faces_array = read_faces(self, faces_data_block, len(faces_data_block))
            # Check for parse failure
            if faces_array is None:
                log.debug("! Failed to parse face data")
                # return mesh_obj
                break

            # Append data to mesh_obj
            mesh_obj.append(
                {
                    "name": str(mi_name),
                    "vertices": {
                        "mesh_obj_number": mesh_obj_number,
                        "mesh_matrices_number": mesh_matrices_number,
                        "mesh_byte_size": mesh_byte_size,
                        "data": vertices_array,
                    },
                    "faces": {"size": faces_data_size, "data": faces_array},
                    "normals": normals,
                    "uvs": uvs,
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
        # self.report({"ERROR"}, f"分割网格数据失败: {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return mesh_obj

# def read_half_float(data, offset):
#     try:
#         value = struct.unpack('H', data[offset:offset + 2])[0]
#         sign = (value >> 15) & 0x1
#         exponent = (value >> 10) & 0x1F
#         mantissa = value & 0x3FF

#         if exponent == 0:
#             return ((-1) ** sign) * (2 ** -14) * (mantissa / 1024)
#         elif exponent == 31:
#             return 0.0  # simplified handling for special values
#         else:
#             return ((-1) ** sign) * (2 ** (exponent - 15)) * (1 + mantissa / 1024)
#     except:
#         return 0.0
