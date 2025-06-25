# mesh_map\utils.py
import struct
import traceback

from .. import tools
from ..log import log


def find_next_head(data, data_start):
    """Find the next object header."""
    # Record incoming data_start
    temp_data_start = data_start
    log.debug(">>>>>>>>>>>>>>>>>>>>>>>> : %s", hex(data_start))
    data_len = len(data)
    log.debug("DATA size: %s", hex(data_len))

    while True:
        if data_start >= data_len:
            log.debug(
                "<<<<<<<<<<<<<<<<<<<<<<<!!! Next object header not found, start: %s",
                hex(temp_data_start),
            )
            return None

        # Read next value
        # log.debug("data_start: %s",hex(data_start))
        tag_ff = data[data_start: data_start + 1][0]
        # log.debug("tag_ff: %s", hex(tag_ff))
        # data_start += 1
        if tag_ff == 0xFF:
            if data_start + 4 < len(data):  # ensure enough bytes to unpack an int
                tag_4ff = struct.unpack_from("<I", data, data_start)[0]
                # log.debug("tag_4ff: %s",hex(tag_4ff))
                if tag_4ff != 0xFFFFFFFF:
                    data_start += 1
                    # log.debug("!= 0xffffffff : %s",hex(data_start))
                else:
                    # log.debug("tag_4ff: %s",hex(tag_4ff))
                    data_start -= 0x30 + 0x1D
                    log.debug(
                        "<<<<<<<<<<<<<<<<<<<<<<< Found next object first matrix end %s",
                        hex(data_start),
                    )
                    return data_start
            else:
                log.debug("Insufficient data to read")
                return None
        else:
            data_start += 1
            # log.debug("!= 0xff : %s",hex(data_start))


def read_map_first_head(self, data):
    """Read the first map header."""
    log.debug(">>> Begin reading first map header")
    # Read position
    data_index = 0

    # Ensure enough data
    if len(data) < 24:
        log.debug("Error: Not enough data")
        return

    # Camera position?
    x1, y1, z1, x2, y2, z2 = struct.unpack_from("<ffffff", data)
    log.debug("Camera 1 Position: x1= %s, y1=%s, z1=%s", x1, y1, z1)
    log.debug("Camera 2 Position: x2=%s, y2=%s, z2=%s", x2, y2, z2)

    # Advance index
    data_index += 24

    return data_index


# Read header helper
def read_head(self, data, start_index):
    """Parse header information."""
    log.debug(">>> Begin reading header")

    # Ensure there are enough bytes to unpack
    if len(data) < start_index + 29:
        log.debug("! Failed to parse header: insufficient bytes at %s", start_index)
        # self.report({"ERROR"}, "Header parse failed")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    # Number of mesh objects (first file only)
    mesh_obj_number = struct.unpack_from("<I", data, start_index)[0]
    # Face group count
    mesh_face_group_number = struct.unpack_from("<I", data, start_index + 4)[0]
    # Matrix count
    mesh_matrices_number = struct.unpack_from("<I", data, start_index + 8)[0]
    # 4-byte zero flag (unused)
    # zeros_tag = struct.unpack_from("<I", data, 36)[0]
    # 1-byte 01 flag (unused)
    # zeroone_tag = struct.unpack_from("<B", data, 48)[0]
    # Total bytes of this mesh
    mesh_byte_size = struct.unpack_from("<I", data, start_index + 25)[0]

    # Print header info
    log.debug(
        "<<< mesh count: %s face groups: %s matrices: %s bytes: %s",
        hex(mesh_obj_number), hex(mesh_face_group_number), hex(mesh_matrices_number), hex(mesh_byte_size)
    )

    # Return mesh count, matrix count and byte size
    return mesh_obj_number, mesh_matrices_number, mesh_byte_size


# Parse vertex data
def read_vertices(self, vertices_data, mesh_matrices_number, mesh_byte_size):
    """Parse vertex data."""
    log.debug(">>> Begin parsing vertex data")
    # Vertex data
    vertices = []
    # Normal data
    normals = []
    # UV coordinate data
    uvs = []

    # Block size (0x34)
    block_size = int(mesh_byte_size / mesh_matrices_number)
    if block_size != 52:
        log.debug("! Failed to compute block size: %s", block_size)
        # self.report({"ERROR"}, "Block size calculation failed")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("> Block size: %s", hex(block_size))

    # Parse vertex data
    try:
        for mni in range(mesh_matrices_number):
            # Calculate current block start
            mniv = block_size * mni
            # Ensure enough bytes to unpack
            if mniv + block_size <= mesh_byte_size:
                vx = struct.unpack_from("f", vertices_data, mniv)[0]
                vy = struct.unpack_from("f", vertices_data, mniv + 4)[0]
                vz = struct.unpack_from("f", vertices_data, mniv + 8)[0]
                # Append vertex
                vertices.append((vx, vy, vz))

                # Read normals
                nx = tools.read_half_float(vertices_data, mniv + 0x0c)
                ny = tools.read_half_float(vertices_data, mniv + 0x0e)
                nz = tools.read_half_float(vertices_data, mniv + 0x10)
                normals.append((nx, ny, nz))
                # log.debug(">> 读取法线数据: %s , %s , %s", nx, ny, nz)

                # Read UV coordinates
                uv_start = mniv + block_size - 0x10
                # log.debug(">> uv_start: %s , mniv : %s ", uv_start, mniv)
                u = tools.read_half_float(vertices_data, uv_start)
                v = tools.read_half_float(vertices_data, uv_start + 0x2)
                uvs.append((u, 1 - v))
                # log.debug(">> 读取UV坐标: %s , %s ", u, 1 - v)
            else:
                log.debug("! Vertex data parse failed: insufficient bytes at %s", mniv)
                break
    except Exception as e:
        log.debug("! Vertex data parse failed: %s", e)
        # self.report({"ERROR"}, f"顶点数据解析失败 : {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< Parsed %s vertex groups", len(vertices))

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
        # self.report({"ERROR"}, f"Face data parse failed: {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return None

    log.debug("<<< Finished reading %s faces", len(faces))

    return faces


# Split mesh data
def split_mesh(self, data):
    """Split mesh data"""
    log.debug(">>> Begin splitting mesh data")
    # Data start offset
    data_start = 0
    # Mesh objects
    mesh_obj = []

    # Read dynamic header
    data_index = read_map_first_head(self, data)
    # Adjust data start position
    data_start = data_index
    log.debug("> fix data start: %s", hex(data_start))

    # Temporary counter
    temp_num = 0

    try:
        while True:
            temp_num += 1

            # Read header information
            read_head_temp = read_head(self, data, data_start)
            # Check for read failure
            if read_head_temp is None:
                log.debug("! Failed to read header")
                # return mesh_obj
                break
            # Parsed header -> mesh object count, matrix count and byte size
            mesh_obj_number, mesh_matrices_number, mesh_byte_size = read_head_temp

            # Get vertex data length
            vertices_data = data[data_start + 0x1D: data_start + 0x1D + mesh_byte_size]
            log.debug("> Vertex data length: %s", hex(len(vertices_data)))
            if len(vertices_data) <= 0:
                log.debug("! Failed to get vertex data length")
                # self.report({"ERROR"}, "Failed to get vertex data length")
                traceback.print_exc()
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
            if faces_data_size >= len(data):
                log.debug(
                    "! Failed to get face block, encountered unknown block! start:%s offset:%s",
                    hex(data_start + 0x1D), hex(data_start + 0x1D + mesh_byte_size)
                )
                break
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

            # Read remaining data (shaders, textures, animation, etc.) -> check for next object header
            find_start = find_next_head(data, data_start)
            if find_start is None:
                log.debug("! Next object header not found, mesh_obj len: %s", hex(len(mesh_obj)))
                break
            data_start = find_start

            log.debug("Finished getting next object header")
            # if not nextobj:
            #     log.debug("! 读取其他物体数据失败")
            #     # self.report({"ERROR"}, "读取其他物体数据失败")
            #     traceback.print_exc()
            #     # return {"CANCELLED"}
            #     break
            # # 修正数据起始位置
            # data_start = next_data_start

            # Check if end of file reached
            if len(mesh_obj) >= mesh_obj[0]["vertices"]["mesh_obj_number"] - 1:
                log.debug("<<< Reached end of data")
                break

        log.debug("Returning mesh_obj")
        return mesh_obj
    except Exception as e:
        log.debug("! Failed to split mesh data: %s", e)
        # self.report({"ERROR"}, f"分割网格数据失败: {e}")
        traceback.print_exc()
        # return {"CANCELLED"}
        return mesh_obj
